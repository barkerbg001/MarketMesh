import { ensureVenv, runManage } from './api-env.mjs'

const args = process.argv.slice(2)
if (args.length === 0) {
  console.error('Usage: npm run manage -- <django-command> [args]')
  process.exit(1)
}

ensureVenv()
runManage(args)
