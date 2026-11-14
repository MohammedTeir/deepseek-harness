import base from '../../../vitest.expected.config.ts'

export default { ...base, test: { ...base.test, include: ['apps/android/tests/web-bootstrap.host.spec.mjs'] } }
