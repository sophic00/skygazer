export const SITE = {
  website: "https://sophic.dev/", // replace this with your deployed domain
  author: "Vaibhav Sijaria",
  profile: "https://sophic.dev/",
  keybase: "https://keybase.io/vaibhav00/",
  desc: "My small place on internet.",
  title: "sophic00",
  ogImage: "img1.jpg",
  lightAndDarkMode: true,
  postPerIndex: 2,
  postPerPage: 4,
  showFeaturedPosts: false,
  showRecentPosts: false,
  showAllPostsButton: false,
  scheduledPostMargin: 15 * 60 * 1000, // 15 minutes
  showArchives: false,
  showBackButton: true, // show back button in post detail
  editPost: {
    enabled: false,
    text: "Edit page",
    url: "https://github.com/satnaing/astro-paper/edit/main/",
  },
  dynamicOgImage: true,
  dir: "ltr", // "rtl" | "auto"
  lang: "en", // html lang code. Set this empty and default will be "en"
  timezone: "Asia/Bangkok", // Default global timezone (IANA format) https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
} as const;
