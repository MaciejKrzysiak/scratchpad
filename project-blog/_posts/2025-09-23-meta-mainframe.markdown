---
layout: post
title: "Meta Mainframe – Self Hosting a Jekyll Blog"
date: 2025-09-23 15:40:11 -0700
author: Maciej
categories: jekyll update
---

> "Share your knowledge. It is a way to achieve immortality." – Dalai Lama xıv

In this post, I continue from [Meta Memoir]({% post_url 2025-09-16-meta-memoir %}), where we first set up the Scratchpad blog. This week, I worked to get it online so I'm not blogging into the void. To make that happen, we need something persistent to host the blog—and that means finding the world's cheapest virtual machine. Thanks to some insider information, [RackNerd][racknerd-bf] has a Black Friday deal year-round, so we can grab a VM for just $18 a year.

Once purchased, I received an email with an IP address, username, root password, and SSH port. To connect, I ran:

`ssh -p <ssh-port> <username>@<ip-address>`

From there, I cloned the Scratchpad repo:

`git clone https://github.com/MaciejKrzysiak/scratchpad.git`

You can try `bundle exec jekyll serve` to get the site up and running, but firewall protections won't allow outside traffic. Instead, we'll need to use ufw, a firewall management tool, to allow access to port 4000.

Run `sudo ufw allow 4000/tcp`, followed by `bundle exec jekyll serve --host 0.0.0.0 --port 4000`, where `--host 0.0.0.0` is the magic that lets us listen for traffic on the public IP.

From a different machine, visiting `http://<ip-address>:4000` should now take you to the blog! Presumably, if you're reading this, you've already found [ScratchPad][scratchpad]. Next week, we'll add some security measures (ó﹏ò｡)

[racknerd-bf]: https://www.racknerd.com/BlackFriday/
[scratchpad]: http://23.94.56.16:4000/
