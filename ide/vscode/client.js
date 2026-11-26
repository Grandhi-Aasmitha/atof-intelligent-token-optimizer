'use strict';
const http = require('node:http');

function localOrigin(raw) {
  const u = new URL(raw);
  if (u.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(u.hostname) ||
      u.username || u.password || u.pathname !== '/' || u.search || u.hash) {
    throw Error('Use a local HTTP origin, for example http://127.0.0.1:8081');
  }
  return u.origin;
}

function request(origin, path, method = 'GET', payload, extraHeaders = {}) {
  const url = new URL(path, localOrigin(origin));
  if (url.origin !== localOrigin(origin)) return Promise.reject(Error('Non-local request blocked'));
  const body = payload === undefined ? undefined : JSON.stringify(payload);
  return new Promise((resolve, reject) => {
    const headers = {...extraHeaders};
    if (body !== undefined) Object.assign(headers, {'Content-Type':'application/json','Content-Length':Buffer.byteLength(body)});
    const req = http.request(url, {method, headers, timeout:12000}, res => {
      let bytes = 0, data = '';
      res.setEncoding('utf8');
      res.on('data', chunk => {
        bytes += Buffer.byteLength(chunk);
        if (bytes > 8000000) req.destroy(Error('ATOF response too large'));
        else data += chunk;
      });
      res.on('error', reject);
      res.on('aborted', () => reject(Error('ATOF response interrupted')));
      res.on('end', () => {
        try {
          if (res.statusCode !== 200) throw Error('Local ATOF returned HTTP '+res.statusCode);
          resolve(JSON.parse(data));
        } catch (e) { reject(e); }
      });
    });
    req.on('timeout', () => req.destroy(Error('Local ATOF timed out')));
    req.on('error', reject);
    req.end(body);
  });
}

module.exports = {localOrigin, request};
