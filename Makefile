RESUME_SRC ?= ../resume/resume-typst.pdf
RESUME_DST ?= static/resume.pdf

.PHONY: resume
resume: ## Copy resume PDF from ../resume into static/
	cp $(RESUME_SRC) $(RESUME_DST)
