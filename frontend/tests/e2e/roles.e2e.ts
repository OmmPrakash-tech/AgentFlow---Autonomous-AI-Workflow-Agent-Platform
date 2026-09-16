import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const fixturePath = process.env.E2E_ACCOUNTS;
if (!fixturePath)
  throw new Error(
    "Set E2E_ACCOUNTS to a local verification-account JSON file. Never commit credentials.",
  );
const accounts = JSON.parse(readFileSync(fixturePath, "utf8"));

for (const role of ["ADMIN", "DEVELOPER", "ANALYST", "VIEWER"]) {
  test(`${role} sees only permitted actions and retains session on refresh`, async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByLabel("Email", { exact: true }).fill(accounts[role].email);
    await page
      .getByLabel("Password", { exact: true })
      .fill(accounts[role].password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.locator(".account")).toContainText(role);
    await page.reload();
    await expect(page.locator(".account")).toContainText(role);
    await page.getByRole("link", { name: "Projects", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Register project", exact: true }),
    ).toHaveCount(["ADMIN", "DEVELOPER"].includes(role) ? 1 : 0);
    await page.getByRole("link", { name: "Agent Runs", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Launch agent run", exact: true }),
    ).toHaveCount(role === "VIEWER" ? 0 : 1);
    await expect(page.locator('option[value="EDIT_MODE"]')).toHaveCount(
      ["ADMIN", "DEVELOPER"].includes(role) ? 1 : 0,
    );
    await page.getByRole("link", { name: "Workflows", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Workflow builder", exact: true }),
    ).toHaveCount(["ADMIN", "DEVELOPER"].includes(role) ? 1 : 0);
    await expect(
      page.locator("nav").getByRole("link", { name: "Activity", exact: true }),
    ).toHaveCount(role === "ADMIN" ? 1 : 0);
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator(".account")).toBeVisible();
    await page.locator(".account").click();
    await expect(
      page.getByRole("heading", { name: "Welcome back." }),
    ).toBeVisible();
  });
}

test("recorded real-Qwen history, live state and report survive refresh", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Email", { exact: true }).fill(accounts.ADMIN.email);
  await page
    .getByLabel("Password", { exact: true })
    .fill(accounts.ADMIN.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account")).toContainText("ADMIN");
  await page.goto("/runs/" + accounts.recordedRunId);
  await expect(
    page.getByText("COMPLETED", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Task graph" })).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("COMPLETED", { exact: true }).first(),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Markdown" }).click();
  const result = await download;
  const content = readFileSync((await result.path())!, "utf8");
  expect(content).toContain("Tests were not executed.");
  expect(content).toContain("calculator.py");
});

for (const kind of ["editApproval", "testApproval"]) {
  test(`${kind}: rejecting a real pending control request prevents execution`, async ({
    page,
  }) => {
    const fixture = accounts[kind];
    expect(
      fixture,
      "Prepare labelled approval fixtures in an isolated verification database",
    ).toBeTruthy();
    await page.goto("/");
    await page
      .getByLabel("Email", { exact: true })
      .fill(accounts.DEVELOPER.email);
    await page
      .getByLabel("Password", { exact: true })
      .fill(accounts.DEVELOPER.password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page.locator(".account")).toContainText("DEVELOPER");
    await page.goto("/runs/" + fixture.runId);
    await expect(
      page.getByRole("button", { name: "Approve exact action" }),
    ).toBeVisible();
    expect(readFileSync(fixture.source, "utf8")).toBe(fixture.original);
    await page.getByRole("button", { name: "Reject", exact: true }).click();
    await expect(
      page.getByText("FAILED", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Approve exact action" }),
    ).toHaveCount(0);
    expect(readFileSync(fixture.source, "utf8")).toBe(fixture.original);
  });
}

test("viewer cannot decide a pending action even through a direct API call", async ({
  page,
}) => {
  const fixture = accounts.viewerApproval;
  expect(fixture).toBeTruthy();
  await page.goto("/");
  await page.getByLabel("Email", { exact: true }).fill(accounts.VIEWER.email);
  await page
    .getByLabel("Password", { exact: true })
    .fill(accounts.VIEWER.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account")).toContainText("VIEWER");
  await page.goto("/runs/" + fixture.runId);
  await expect(
    page.getByText(
      "Your role can view this request but cannot approve or reject it.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve exact action" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Cancel execution" }),
  ).toHaveCount(0);
  const status = await page.evaluate(async (f) => {
    const response = await fetch("/api/runs/" + f.runId + "/approval", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + sessionStorage.getItem("agentflow-token"),
      },
      body: JSON.stringify({ approvalId: f.approvalId, approved: true }),
    });
    return response.status;
  }, fixture);
  expect(status).toBe(403);
  expect(readFileSync(fixture.source, "utf8")).toBe(fixture.original);
});
