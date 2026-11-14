import { readForm, todayISO } from "../forms.js";
import { setupModule } from "./base.js";

export function initCompound() {
  const ctl = setupModule({ module: "compound", buildPayload: (f) => readForm(f) });
  ctl.form.elements.start_date.value = todayISO();
  ctl.run();
  return ctl;
}
