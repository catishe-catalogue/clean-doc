import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PricingPage from "./page";

describe("PricingPage", () => {
  it("renders pricing headings and all three tiers", () => {
    render(<PricingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toBeDefined();
    expect(screen.getByText("Тарифные планы и оплата")).toBeDefined();
    expect(screen.getByText("0 ₽")).toBeDefined();
    expect(screen.getByText("1 490 ₽")).toBeDefined();
    expect(screen.getByText("11 900 ₽")).toBeDefined();
    expect(screen.getByText("Выставить счет по ИНН")).toBeDefined();
  });
});
