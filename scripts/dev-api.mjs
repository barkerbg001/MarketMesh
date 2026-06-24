import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const apiDir = join(process.cwd(), 'api')
const venvPython =
  process.platform === 'win32'
    ? join(apiDir, '.venv', 'Scripts', 'python.exe')
    : join(apiDir, '.venv', 'bin', 'python')

if (!existsSync(venvPython)) {
  console.error(
    [
      'API virtual environment not found.',
      'Run: npm run setup:api',
      `Expected: ${venvPython}`,
    ].join('\n'),
  )
  process.exit(1)
}

const uvicornArgs = ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000']

// Uvicorn reload is unreliable on Windows and can leave zombie processes on port 8000.
if (process.platform !== 'win32') {
  uvicornArgs.push('--reload')
}

const child = spawn(venvPython, uvicornArgs, {
  cwd: apiDir,
  stdio: 'inherit',
  env: process.env,
})

child.on('error', (error) => {
  console.error('Failed to start API:', error.message)
  process.exit(1)
})

child.on('exit', (code) => process.exit(code ?? 1))
