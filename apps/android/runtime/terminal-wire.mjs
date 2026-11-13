// Private native broker transport. Never carries an agent-generated decision.
import net from 'node:net';
export function terminalRequest(action, fields = {}, signal) {
  let cancellation;
  const pending = new Promise((resolve, reject) => {
    const socket = net.createConnection({ path: (process.platform === 'android' ? '\0' : '') + process.env.HARNESS_TERMINAL_SOCKET });
    let data = '';
    const abort = () => {
      if (!cancellation && action !== 'cancel' && fields.callId) {
        cancellation = terminalRequest('cancel', fields).then(reply => { if (!reply.ok) throw new Error('Native cancellation not acknowledged'); });
      }
      socket.destroy(new Error('Native request cancelled'));
    };
    signal?.addEventListener('abort', abort, { once: true });
    socket.setTimeout(action === 'cancel' ? 10000 : 70000, () => socket.destroy(new Error('Native broker deadline')));
    socket.once('connect', () => {
      if (signal?.aborted) return abort();
      socket.write(JSON.stringify({ version: 1, token: process.env.HARNESS_TERMINAL_SECRET, action, ...fields }) + '\n');
    });
    socket.on('data', chunk => {
      data += chunk.toString('utf8');
      if (data.length > 32768) socket.destroy(new Error('Native reply exceeds limit'));
      if (data.endsWith('\n')) socket.end();
    });
    socket.once('error', reject);
    socket.once('close', hadError => {
      signal?.removeEventListener('abort', abort);
      if (hadError) return;
      try { resolve(JSON.parse(data)); } catch (error) { reject(error); }
    });
  });
  return pending.catch(async error => {
    if (!cancellation && action !== 'cancel' && fields.callId) {
      cancellation = terminalRequest('cancel', fields).then(reply => { if (!reply.ok) throw new Error('Native cancellation not acknowledged'); });
    }
    if (cancellation) await cancellation;
    throw error;
  });
}
