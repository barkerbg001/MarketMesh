import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

export const apiDir = join(process.cwd(), 'api')
export const venvDir = join(apiDir, '.venv')
export const venvPython =
  process.platform === 'win32'
    ? join(venvDir, 'Scripts', 'python.exe')
    : join(venvDir, 'bin', 'python')

export function ensureVenv() {
  if (!existsSync(venvPython)) {
    console.error(
      ['API virtual environment not found.', 'Run: npm run setup:api', `Expected: ${venvPython}`].join(
        '\n',
      ),
    )
    process.exit(1)
  }
}

export function runManageSync(args) {
  const result = spawnSync(venvPython, ['manage.py', ...args], { cwd: apiDir, stdio: 'inherit' })
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

export function runManage(args) {
  const child = spawn(venvPython, ['manage.py', ...args], {
    cwd: apiDir,
    stdio: 'inherit',
    env: process.env,
  })
  child.on('error', (error) => {
    console.error('Failed to start manage.py:', error.message)
    process.exit(1)
  })
  child.on('exit', (code) => process.exit(code ?? 1))
}
