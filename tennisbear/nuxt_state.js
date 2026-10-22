// テニスベアの HTML に埋め込まれた window.__NUXT__ を取り出して JSON で出力する。
// __NUXT__ は値を引数で渡す即時関数なので、外部へのアクセス手段を持たない vm の中で評価する。
const fs = require("fs");
const vm = require("vm");

const html = fs.readFileSync(0, "utf8");
const m = html.match(/<script>(window\.__NUXT__=[\s\S]*?)<\/script>/);
if (!m) {
  process.stderr.write("window.__NUXT__ not found\n");
  process.exit(1);
}
const ctx = { window: {} };
vm.runInNewContext(m[1], ctx, { timeout: 2000 });
process.stdout.write(JSON.stringify(ctx.window.__NUXT__));
