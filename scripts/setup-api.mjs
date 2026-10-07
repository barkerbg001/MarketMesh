import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'

import { apiDir, runManageSync, venvPython } from './api-env.mjs'

function run(command, args) {
  const result = spawnSync(command, args, { cwd: apiDir, stdio: 'inherit' })
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

if (!existsSync(venvPython)) {
  console.log('Creating API virtual environment...')
  run(process.platform === 'win32' ? 'python' : 'python3', ['-m', 'venv', '.venv'])
}

console.log('Installing API dependencies...')
run(venvPython, ['-m', 'pip', 'install', '--upgrade', 'pip'])
run(venvPython, ['-m', 'pip', 'install', '-r', 'requirements.txt'])

console.log('Installing Playwright Chromium for retailer scraping...')
run(venvPython, ['-m', 'playwright', 'install', 'chromium'])

console.log('Applying database migrations...')
runManageSync(['migrate', '--noinput'])

console.log('API setup complete.')
