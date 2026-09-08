/** Trusted Pi adapter. Launch with --no-builtin-tools so load failure is closed. */
import { execFile } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const bridge = fileURLToPath(new URL('./isolated_tools.py', import.meta.url));
export default function register(pi) {
  const container = process.env.SKILL_EVAL_CONTAINER;
  const docker = process.env.SKILL_EVAL_DOCKER;
  const python = process.env.SKILL_EVAL_PYTHON;
  if (!/^skill-eval-offline-[a-f0-9]{32}$/.test(container || '') || !docker?.startsWith('/') || !python?.startsWith('/')) {
    throw new Error('Isolated worker configuration required; host tools are unavailable');
  }
  const properties = {
    read: {path: {type:'string'}, offset: {type:'integer', minimum:1}, limit: {type:'integer', minimum:1}},
    write: {path: {type:'string'}, content: {type:'string'}},
    edit: {path: {type:'string'}, oldText: {type:'string', minLength:1}, newText: {type:'string'}},
    bash: {command: {type:'string'}, timeout: {type:'integer', minimum:1, maximum:60}},
  };
  const required = {read:['path'], write:['path','content'], edit:['path','oldText','newText'], bash:['command']};
  for (const name of Object.keys(properties)) {
    pi.registerTool({
      name, label:name, description:`${name} inside the offline evaluation worker. Files: /workspace and read-only /skills. No host files or network.`,
      parameters: {type:'object', properties:properties[name], required:required[name], additionalProperties:false},
      execute: async (_id, params, signal) => {
        const result = await new Promise((resolve, reject) => {
          const env = Object.fromEntries(['HOME','PATH','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG'].filter(k => process.env[k]).map(k => [k,process.env[k]]));
          const child = execFile(python, ['-I',bridge,'--worker',container,'--docker',docker],
            {env, timeout:70000, maxBuffer:16*1024*1024, signal},
            (error, stdout, stderr) => error ? reject(new Error(`Isolated tool failed: ${stderr.slice(0,2000)}`)) : resolve(JSON.parse(stdout)));
          child.stdin.end(JSON.stringify({op:name, ...params}));
        });
        return {content:[{type:'text', text:result.text}], details:{}, isError:result.isError || false};
      },
    });
  }
}
