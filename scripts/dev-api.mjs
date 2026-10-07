import { ensureVenv, runManage, runManageSync } from './api-env.mjs'

ensureVenv()
runManageSync(['migrate', '--noinput'])
runManage(['runserver', '127.0.0.1:8000'])
