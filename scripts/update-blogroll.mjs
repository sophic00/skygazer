#!/usr/bin/env node

import Parser from 'rss-parser';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

const parser = new Parser({
  timeout: 10000,
  headers: {
    'User-Agent': 'Mozilla/5.0 (compatible; BlogrollBot/1.0)',
  },
});

function loadExistingData() {
  const outputPath = join(process.cwd(), 'src/data/blogroll.json');
  if (!existsSync(outputPath)) {
    return {};
  }
  
  try {
    const data = readFileSync(outputPath, 'utf-8');
    const blogrollData = JSON.parse(data);
    
    // Create a map of feedUrl -> existing data for quick lookup
    const existingDataMap = {};
    blogrollData.forEach(blog => {
      existingDataMap[blog.feedUrl] = {
        ...blog,
        seenPosts: new Set(blog.latestPosts.map(post => post.link))
      };
    });
    
    return existingDataMap;
  } catch (error) {
    console.warn('Could not load existing data:', error.message);
    return {};
  }
}

function mergePosts(existingPosts, newPosts, maxPosts = 10) {
  const seenLinks = new Set();
  const mergedPosts = [];
  
  // Combine existing and new posts
  const allPosts = [...existingPosts, ...newPosts];
  
  // Sort by date (newest first) and deduplicate
  allPosts
    .sort((a, b) => {
      const dateA = new Date(a.pubDate || 0);
      const dateB = new Date(b.pubDate || 0);
      return dateB.getTime() - dateA.getTime();
    })
    .forEach(post => {
      if (!seenLinks.has(post.link) && mergedPosts.length < maxPosts) {
        seenLinks.add(post.link);
        mergedPosts.push(post);
      }
    });
  
  return mergedPosts;
}

async function fetchBlogroll() {
  const rollPath = join(process.cwd(), 'roll.txt');
  
  let rollContent;
  try {
    rollContent = readFileSync(rollPath, 'utf-8');
  } catch (error) {
    console.error('Error reading roll.txt:', error);
    return [];
  }

  const feedUrls = rollContent
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'));

  // Load existing data for incremental updates
  const existingData = loadExistingData();
  const blogrollEntries = [];

  for (const feedUrl of feedUrls) {
    const existing = existingData[feedUrl];
    
    try {
      console.log(`Fetching feed: ${feedUrl}`);
      const feed = await parser.parseURL(feedUrl);
      
      const newPosts = (feed.items || [])
        .map(item => ({
          title: item.title || 'Untitled',
          link: item.link || '',
          pubDate: item.pubDate || item.isoDate || '',
          contentSnippet: item.contentSnippet?.substring(0, 200) || '',
          creator: item.creator || item['dc:creator'] || '',
        }));

      // Merge with existing posts to avoid losing content and prevent duplicates
      const existingPosts = existing ? existing.latestPosts : [];
      const mergedPosts = mergePosts(existingPosts, newPosts, 10);
      
      // Check if we have new content
      const hasNewContent = existing ? 
        newPosts.some(post => !existing.seenPosts.has(post.link)) : 
        true;
        
      if (hasNewContent || !existing) {
        console.log(`  → Found ${newPosts.length} posts, ${hasNewContent ? 'has new content' : 'no new content'}`);
      }

      blogrollEntries.push({
        feedUrl,
        title: feed.title || existing?.title || 'Unknown Feed',
        siteUrl: feed.link || existing?.siteUrl || feedUrl,
        description: feed.description || existing?.description || '',
        latestPosts: mergedPosts,
        lastUpdated: new Date().toISOString(),
        lastFetched: existing?.lastFetched || new Date().toISOString(),
      });

      // Add small delay to be respectful to servers
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      console.error(`Error fetching feed ${feedUrl}:`, error);
      
      // If we have existing data for this feed, keep it instead of losing it
      if (existing) {
        console.log(`  → Using cached data for ${feedUrl}`);
        blogrollEntries.push({
          ...existing,
          seenPosts: undefined, // Remove the Set from the output
          lastUpdated: existing.lastUpdated, // Keep original update time
          lastFetched: new Date().toISOString(), // Update fetch attempt time
        });
      }
      // If no existing data, skip this feed (it will be retried next time)
    }
  }

  // Save the updated data
  const outputPath = join(process.cwd(), 'src/data/blogroll.json');
  writeFileSync(outputPath, JSON.stringify(blogrollEntries, null, 2));
  
  const totalPosts = blogrollEntries.reduce((sum, blog) => sum + blog.latestPosts.length, 0);
  console.log(`Blogroll data saved to ${outputPath}`);
  console.log(`Total: ${blogrollEntries.length} feeds, ${totalPosts} posts`);
  return blogrollEntries;
}

fetchBlogroll()
  .then(() => {
    console.log('Blogroll update completed');
    process.exit(0);
  })
  .catch(error => {
    console.error('Error updating blogroll:', error);
    process.exit(1);
  });