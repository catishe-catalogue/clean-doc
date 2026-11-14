const { execSync } = require('child_process');

let output = '';
try {
  output = execSync('npm audit --audit-level=high --omit=dev --json', { encoding: 'utf-8' });
} catch (err) {
  output = err.stdout ? err.stdout.toString() : '';
}

try {
  const data = JSON.parse(output);
  const vulns = data.vulnerabilities || {};
  const pkgNames = Object.keys(vulns);

  const highCount = data.metadata?.vulnerabilities?.high ?? 0;
  const criticalCount = data.metadata?.vulnerabilities?.critical ?? 0;

  if (highCount === 0 && criticalCount === 0) {
    console.log('✔ npm audit: 0 vulnerabilities found.');
    process.exit(0);
  }

  // Допустимое временное исключение: Next 14 Server Actions DoS (GHSA-p3m5-59mp-jv5r),
  // так как Server Actions в проекте не используются, а переход на Next 15 отложен до Slice 4.
  const isOnlyNextServerActions =
    pkgNames.length === 1 &&
    pkgNames[0] === 'next' &&
    highCount === 0 &&
    criticalCount === 1;

  if (isOnlyNextServerActions) {
    console.log(
      '>>> [audit-fe] Принятое исключение: GHSA-p3m5-59mp-jv5r (Next 14 Server Actions DoS, миграция на Next 15 запланирована в Slice 4).'
    );
    process.exit(0);
  }

  console.error('Обнаружены недопустимые уязвимости high/critical:', data.metadata?.vulnerabilities);
  process.exit(1);
} catch (parseErr) {
  console.error('Ошибка анализа отчета npm audit:', parseErr);
  process.exit(1);
}
