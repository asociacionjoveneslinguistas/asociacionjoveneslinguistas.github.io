// Contacto: sends the four fields to the association's Google Form and reports the result in place.
// Google answers an opaque response (no-cors), so «sent» means the request left the browser; the fields are validated here first.
(() => {
  const form = document.getElementById("cform");
  if (!form) return;
  const status = form.querySelector(".cform__status");
  const button = form.querySelector(".cform__send");
  const fields = [...form.querySelectorAll("[name^='entry.']")];
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const blank = fields.find((f) => !f.value.trim());
    if (blank) { blank.value = ""; form.reportValidity(); return; }
    if (form.elements.web.value) return;
    const body = new URLSearchParams();
    fields.forEach((f) => body.append(f.name, f.value.trim()));
    button.disabled = true;
    status.dataset.state = "";
    status.textContent = form.dataset.sending;
    try {
      await fetch(form.action, { method: "POST", mode: "no-cors", body });
      form.reset();
      status.dataset.state = "ok";
      status.textContent = form.dataset.sent;
    } catch (err) {
      status.dataset.state = "error";
      status.textContent = form.dataset.error;
    } finally {
      button.disabled = false;
    }
  });
})();
