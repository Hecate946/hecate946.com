faviscon: https://www.svgrepo.com/svg/500124/duck

local stats server: cd cloudflare/stats-worker && npx wrangler dev

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