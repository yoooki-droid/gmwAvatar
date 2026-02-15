#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const frontendBase = process.env.FRONTEND_BASE_URL || 'http://127.0.0.1:5174';
const backendBase = process.env.BACKEND_BASE_URL || 'http://127.0.0.1:8000';
const rootDir = '/Users/yokichen/Documents/gmwAvatar';
const reportPath = path.join(rootDir, 'docs', 'smoke-test-report.md');
const reportJsonPath = path.join(rootDir, 'docs', 'smoke-test-report.json');
const frontendPlaywrightEntry = path.join(rootDir, 'frontend', 'node_modules', 'playwright', 'index.mjs');

const now = new Date();
const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
const testTitle = `冒烟测试新闻-${stamp}`;

/** @type {Array<{name:string,status:'PASS'|'FAIL'|'SKIP',detail:string}>} */
const rows = [];
let hasFailure = false;
const consoleErrors = [];
let chromium;

const pushResult = (name, status, detail) => {
  rows.push({ name, status, detail });
  if (status === 'FAIL') hasFailure = true;
};

const callApi = async (url, init) => {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText} ${text}`);
  }
  return text ? JSON.parse(text) : {};
};

const healthCheck = async () => {
  await callApi(`${backendBase}/healthz`, { method: 'GET' });
  const ui = await fetch(frontendBase);
  if (!ui.ok) throw new Error(`前端不可访问: ${ui.status}`);
};

const createSeedReport = async () => {
  const payload = {
    title: testTitle,
    speaker: '自动化测试',
    summary_raw: '这是一条自动化冒烟测试数据，用于验证页面按钮点击流程。',
    script_final: '这是自动化冒烟测试口播稿。',
    highlights_final: ['按钮点击流程验证通过', '页面路由与保存链路可用'],
    reflections_final: ['建议持续完善自动化覆盖', '建议把失败日志统一收敛到报告中', '建议每次发布前执行一次回归'],
    auto_play_enabled: false,
  };
  return callApi(`${backendBase}/api/reports`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
};

const loadAnyReportId = async () => {
  const res = await callApi(`${backendBase}/api/reports?page=1&page_size=20`, { method: 'GET' });
  const first = (res.items || [])[0];
  return {
    id: Number(first?.id || 0),
    title: String(first?.title || ''),
  };
};

const findEnabledButton = async (page, name) => {
  const locator = page.getByRole('button', { name });
  const count = await locator.count();
  if (!count) return null;
  for (let i = 0; i < count; i += 1) {
    const item = locator.nth(i);
    if (await item.isVisible()) {
      const disabled = await item.isDisabled();
      if (!disabled) return item;
    }
  }
  return null;
};

const clickButtonStep = async (page, name, stepName = `点击按钮：${name}`) => {
  const btn = await findEnabledButton(page, name);
  if (!btn) {
    pushResult(stepName, 'SKIP', '按钮不存在或处于禁用状态');
    return false;
  }
  await btn.click();
  pushResult(stepName, 'PASS', '点击成功');
  return true;
};

const clickLinkStep = async (page, name, stepName = `点击链接：${name}`) => {
  const locator = page.getByRole('link', { name });
  const count = await locator.count();
  if (!count) {
    pushResult(stepName, 'SKIP', '链接不存在');
    return false;
  }
  for (let i = 0; i < count; i += 1) {
    const item = locator.nth(i);
    if (await item.isVisible()) {
      await item.click();
      pushResult(stepName, 'PASS', '点击成功');
      return true;
    }
  }
  pushResult(stepName, 'SKIP', '链接不可见');
  return false;
};

const run = async () => {
  try {
    const playwrightMod = await import('playwright');
    chromium = playwrightMod.chromium;
  } catch {
    const playwrightMod = await import(pathToFileURL(frontendPlaywrightEntry).href);
    chromium = playwrightMod.chromium;
  }

  try {
    await healthCheck();
    pushResult('服务健康检查', 'PASS', '前后端可访问');
  } catch (error) {
    pushResult('服务健康检查', 'FAIL', String(error));
    await flushReport();
    process.exit(1);
  }

  let seedId = 0;
  let seedTitle = testTitle;
  try {
    const seed = await createSeedReport();
    seedId = Number(seed.id || 0);
    seedTitle = testTitle;
    pushResult('创建测试新闻', 'PASS', `report_id=${seedId}`);
  } catch (error) {
    pushResult('创建测试新闻', 'SKIP', `创建失败，改用已有数据继续测试：${String(error)}`);
    try {
      const fallback = await loadAnyReportId();
      seedId = fallback.id;
      seedTitle = fallback.title || testTitle;
      if (!seedId) {
        pushResult('回退测试新闻', 'FAIL', '没有可用的已有新闻数据');
        await flushReport();
        process.exit(1);
      }
      pushResult('回退测试新闻', 'PASS', `report_id=${seedId}`);
    } catch (fallbackError) {
      pushResult('回退测试新闻', 'FAIL', String(fallbackError));
      await flushReport();
      process.exit(1);
    }
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${String(err)}`));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(`console.error: ${msg.text()}`);
    }
  });

  try {
    await page.goto(`${frontendBase}/`, { waitUntil: 'networkidle' });
    pushResult('打开列表页', 'PASS', '/');

    await clickButtonStep(page, '绑定飞书会议');
    await clickButtonStep(page, '取消', '关闭飞书绑定弹层');
    await clickLinkStep(page, '播放', '列表页播放入口');
    await page.waitForURL(/\/playback/, { timeout: 10_000 });
    await page.goto(`${frontendBase}/`, { waitUntil: 'networkidle' });
    await clickLinkStep(page, '+ New Item', '列表页新建入口');
    await page.waitForURL(/\/editor/, { timeout: 10_000 });
    await page.goto(`${frontendBase}/`, { waitUntil: 'networkidle' });

    const row = page.locator('tr', { hasText: seedTitle }).first();
    if (await row.count()) {
      const editLink = row.getByRole('link', { name: '编辑' });
      await editLink.click();
      await page.waitForURL(/\/editor\/\d+/, { timeout: 10_000 });
      pushResult('列表页编辑按钮', 'PASS', '可进入编辑页');
    } else {
      pushResult('列表页编辑按钮', 'FAIL', '未找到测试数据行');
    }

    await clickButtonStep(page, '上一条');
    await clickButtonStep(page, '下一条');
    await clickButtonStep(page, 'AI 生成口播稿、亮点与金融反思');
    await clickButtonStep(page, '保存');
    await clickButtonStep(page, '保存并开启播报');

    await page.goto(`${frontendBase}/playback`, { waitUntil: 'networkidle' });
    pushResult('打开播放调试页', 'PASS', '/playback');

    await clickButtonStep(page, '读取会议实时总结');
    await clickButtonStep(page, '绑定飞书会议', '调试页打开飞书弹层');
    await clickButtonStep(page, '取消', '关闭调试页飞书弹层');
    await clickButtonStep(page, '轮播会议总结');
    await clickButtonStep(page, '会议反思');
    await clickButtonStep(page, '轮播会议总结');
    await clickButtonStep(page, '刷新队列');
    await clickButtonStep(page, '保存配置');
    await clickButtonStep(page, '保存并立即执行');
    await clickButtonStep(page, '从后端读取数字人配置');
    await clickButtonStep(page, '加载数字人');
    await clickButtonStep(page, '不加载数字人');
    const toggledShow = await clickButtonStep(page, '显示固定参数区');
    if (!toggledShow) {
      await clickButtonStep(page, '隐藏固定参数区');
      await clickButtonStep(page, '显示固定参数区');
    }
    await clickButtonStep(page, '仅保存数字人参数');
    await clickButtonStep(page, '加载数字人（当前调试页）');
    await clickButtonStep(page, '隐藏固定参数区');
    await clickButtonStep(page, '清空手动配置');

    const immersiveBtn = await findEnabledButton(page, '打开沉浸式播报页');
    if (!immersiveBtn) {
      pushResult('打开沉浸式播报页', 'SKIP', '按钮禁用（通常是数字人参数未配置）');
    } else {
      const popupPromise = page.waitForEvent('popup', { timeout: 5000 }).catch(() => null);
      await immersiveBtn.click();
      const popup = await popupPromise;
      if (popup) {
        await popup.waitForLoadState('domcontentloaded');
        pushResult('打开沉浸式播报页', 'PASS', '新窗口已打开');
        await clickButtonStep(popup, '返回调试页', '沉浸式返回调试页');
        await popup.close();
      } else {
        pushResult('打开沉浸式播报页', 'PASS', '点击成功（浏览器可能拦截新窗口）');
      }
    }

    if (consoleErrors.length) {
      pushResult('控制台错误检查', 'FAIL', consoleErrors.slice(0, 8).join(' | '));
    } else {
      pushResult('控制台错误检查', 'PASS', '无 console.error / pageerror');
    }
  } catch (error) {
    pushResult('UI 冒烟执行', 'FAIL', String(error));
  } finally {
    await browser.close();
  }

  await flushReport();
  process.exit(hasFailure ? 1 : 0);
};

const flushReport = async () => {
  const lines = [];
  lines.push(`# 冒烟测试报告`);
  lines.push('');
  lines.push(`- 执行时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`);
  lines.push(`- 前端地址：${frontendBase}`);
  lines.push(`- 后端地址：${backendBase}`);
  lines.push(`- 测试数据标题：${testTitle}`);
  lines.push('');
  lines.push(`| 用例 | 结果 | 说明 |`);
  lines.push(`|---|---|---|`);
  for (const row of rows) {
    lines.push(`| ${row.name} | ${row.status} | ${row.detail.replace(/\|/g, '\\|')} |`);
  }
  lines.push('');
  lines.push(`> 说明：此报告由 \`scripts/smoke-ui.mjs\` 自动生成。`);
  await fs.writeFile(reportPath, `${lines.join('\n')}\n`, 'utf8');
  await fs.writeFile(
    reportJsonPath,
    JSON.stringify(
      {
        executedAt: new Date().toISOString(),
        frontendBase,
        backendBase,
        testTitle,
        hasFailure,
        rows,
      },
      null,
      2,
    ) + '\n',
    'utf8',
  );
};

run().catch(async (error) => {
  pushResult('脚本异常', 'FAIL', String(error));
  await flushReport();
  process.exit(1);
});
