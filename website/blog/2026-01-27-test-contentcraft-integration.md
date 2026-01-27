---
slug: test-contentcraft-integration
title: Testing ContentCraft Blog Integration for UAPK
authors: [davidsanker]
tags: [test, contentcraft, blog, uapk]
date: 2026-01-27
---

# Testing ContentCraft Blog Integration

This is a test post created to verify that the ContentCraft blog publishing system works correctly with UAPK's Docusaurus blog.

## About UAPK

The Universal AI Processing Key (UAPK) is a revolutionary system for fair compensation of content creators whose work trains AI models.

## Integration Features

- **Docusaurus Format**: Posts use Docusaurus blog plugin format with proper frontmatter
- **SSH Publishing**: Files written via SSH to UAPK VM
- **GitHub Pages**: Deployed via GitHub Pages after build
- **Author System**: References author ID from `authors.yml`

## Publishing Workflow

1. ContentCraft generates UAPK blog content
2. UAPKBlogPublisher SSH connects to UAPK VM (34.28.188.119)
3. Writes post to `/home/dsanker/uapk-gateway/website/blog/`
4. Docusaurus builds the static site
5. Deployment to uapk.info via GitHub Pages

## Multi-VM Architecture

ContentCraft now supports:
- **Projects VM** (morpheusmark, lawkraft, huckesanker) - API publishing
- **Local Machine** (mother_ai) - Direct file writes
- **UAPK VM** (uapk) - SSH file writes

All from a single CLI command!

## Test Verification

If you're reading this on uapk.info, the integration is working perfectly!

---

**Note:** This is a manual test post created on 2026-01-27 to verify the UAPK blog publishing pipeline.
