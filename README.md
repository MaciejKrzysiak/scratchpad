# Scratchpad Website Project

## Blog

### Jekyll
Jekyll is open source project that runs the blog. To refresh the blog, run: 

```sh
bundle exec jekyll serve --host 0.0.0.0 --port 4000
```

### Hedgedoc
Hedgedoc is another community driven project for editing markdown files on the web. It supports auth via Github/Google and is perfect for adding blog posts.
Hedgedoc is accessible via the subdomain md.scratchpad.lol, where md stands for markdown. The domain registrar (i forgot which one, hosted by Alex) is where
the subdomain is configured for external WAN access and traffic is routed to the internal app via nginx. Nginx configs are edited in:

```sh
/etc/nginx/sites-available/scratchpad
```
 
Currently, Hedgedoc is built off the base docker image provided and config is in 
```sh
scratchpad/hedgedoc/docker-compose.yml
```

### Publisher
The publisher is a service for the blog that bridges hedgedoc and jekyll together. It is a custom build fast-api server (python) running in a docker container. 
The goal of the publisher is to enable Scratchpad blog posters to take drafts in hedgedoc and post them to Jekyll in the _posts directory. 
Configuration for the container is found in: 

```sh  
scratchpad/hedgedoc/docker-compose.yml
```

