// Vercel 빌드 시 환경변수 API_BASE_URL을 public/config.js 로 주입한다.
// (정적 사이트는 브라우저에서 process.env를 읽을 수 없기 때문)
const fs = require("fs");
const path = require("path");

const raw = process.env.API_BASE_URL;
if (!raw && process.env.VERCEL) {
  console.error("API_BASE_URL 환경변수가 설정되지 않았습니다. (Vercel > Settings > Environment Variables)");
  process.exit(1);
}
const url = (raw || "http://localhost:8000").replace(/\/+$/, "");
const out = path.join(__dirname, "public", "config.js");
fs.writeFileSync(out, `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: url })};\n`);
console.log(`config.js 생성 완료: API_BASE_URL=${url}`);
