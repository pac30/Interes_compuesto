import { readForm } from "../forms.js";
import { setupModule } from "./base.js";

export function initRates() {
  const ctl = setupModule({ module: "rates", buildPayload: (f) => readForm(f) });
  ctl.run();
  return ctl;
}
