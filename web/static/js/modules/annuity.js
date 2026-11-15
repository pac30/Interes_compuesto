import { applyConditions, readForm, setFormValues, todayISO } from "../forms.js";
import { setupModule } from "./base.js";

const EXAMPLE = {
  mode: "cuota_pv", annuity_type: "vencida", pv: "10000000", fv: "10000000", cuota: "500000", rate_value: "18",
  pay_period_months: "1", term_value: "24", term_unit: "months", n_cuotas: "", end_date: "",
  insurance_type: "none", insurance_value: "0.05", birth_date: "", age: "",
};

export function initAnnuity() {
  const ctl = setupModule({ module: "annuity", buildPayload: (f) => readForm(f) });
  const f = ctl.form;
  const setToday = () => { f.elements.start_date.value = todayISO(); };
  setToday();

  const birth = f.elements.birth_date, age = f.elements.age, start = f.elements.start_date;
  const calcAge = () => {
    if (!birth.value) return;
    const ref = start.value ? new Date(start.value + "T00:00:00") : new Date();
    const b = new Date(birth.value + "T00:00:00");
    let a = ref.getFullYear() - b.getFullYear();
    if (ref.getMonth() < b.getMonth() || (ref.getMonth() === b.getMonth() && ref.getDate() < b.getDate())) a--;
    age.value = a >= 0 ? a : "";
  };
  birth.addEventListener("change", calcAge);
  start.addEventListener("change", calcAge);

  f.querySelector('[data-action="example"]').addEventListener("click", () => {
    setFormValues(f, EXAMPLE);
    setToday();
    ctl.run({ focus: true });
  });

  // abrir una simulación proveniente de la comparación
  window.addEventListener("open-annuity", (e) => {
    setFormValues(f, e.detail);
    applyConditions(f);
    ctl.run({ focus: true }).then(() => ctl.showTab("proc"));
  });
  ctl.run();
  return ctl;
}
