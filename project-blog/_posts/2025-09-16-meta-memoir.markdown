---
layout: post
title: "Meta Memoir"
date: 2025-09-16 15:40:11 -0700
author: Maciej
categories: jekyll update
---

> "If a tree falls in a forest and no one is around to hear it, does it make a sound?" - Tony Soprano

Scratchpad is on its 15th session and has seen some amazing projects. Unfortunately, unless we capture them in one place, they are lost to the wind. That's why I decided to create this blog. It will serve as a place for members to track their progress and share what they've learned with others. My hope is that, as the number of sessions and members grows, a long archive of projects will motivate us to keep hacking.

For the inaugural post, let's talk about how this blog was set up!

At its core, this blog was built using [Jekyll][jekyll-docs] - a lightweight, static site generator. It is perfect for sites serving text content. Jekyll itself is built using [Ruby][ruby-docs], a high-level programming language similar to Python.

I decided to go with Jekyll for now, as I want this site up sooner rather than later. As Scratchpad's need for dynamic content grows, we might need to migrate. For now, the simplicity of adding new posts will serve us well.

To get things up and running, I needed to:

- [Install Ruby][ruby-install]
  - On a Windows machine, this is handled pretty well for you with the [RubyInstaller for Windows][ruby-windows-install] tool.
- [Install RubyGems][ruby-gem-install], Ruby's package management solution.
- Use RubyGems to install the Jekyll Bundler.
  - `gem install jekyll bundler`
- Create a blank blog titled "project-blog".
  - `jekyll new project-blog`
- Run the executable,
  - `cd project-blog`
  - `bundle exec jekyll serve`

Assuming that works as expected, your http://localhost:4000 will now host the empty blog!

Next we'll want to create a post. Your 'project-blog' directory comes with a convenient '\_posts' directory. Any new markdown file added here will automagically appear on the site. This blog post is in that folder.

Jekyll requires blog post files to be named according to the following format:

`YEAR-MONTH-DAY-title.MARKUP`

Where `YEAR` is a four-digit number, `MONTH` and `DAY` are both two-digit numbers, and `MARKUP` is the file extension representing the format used in the file.

I'll host this blog in a scratchpad repo eventually and share that link here, happy hacking!

[jekyll-docs]: https://jekyllrb.com/docs/home
[jekyll-gh]: https://github.com/jekyll/jekyll
[ruby-docs]: https://www.ruby-lang.org/en/documentation/
[ruby-install]: https://www.ruby-lang.org/en/documentation/installation/
[ruby-windows-install]: https://rubyinstaller.org/
[ruby-gem-install]: https://rubygems.org/pages/download
