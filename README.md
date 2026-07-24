https://www.svgrepo.com/svg/500124/duck


zipper:

zip -r hecate946-site.zip . \
  -x "node_modules/*" \
     "dist/*" \
     ".astro/*" \
     ".git/*" \
     ".env" \
     "secrets.txt" \
     "hecate946-site.zip" \
     "cloudflare/stats-worker/node_modules/*" \
     "cloudflare/stats-worker/.wrangler/*" \
     "cloudflare/stats-worker/.dev.vars"