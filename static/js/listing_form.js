(() => {
  "use strict";

  const form = document.querySelector("[data-listing-form]");
  if (!form) {
    return;
  }

  const disclosure = form.querySelector("[name='defect_disclosure']");
  const dependentGroups = Array.from(form.querySelectorAll("[data-defect-dependent]"));
  const defectInputs = Array.from(form.querySelectorAll("[name='defects']"));
  const details = form.querySelector("[name='defect_details']");
  const primaryInput = form.querySelector("input[type='file'][name='image']");
  const extraInput = form.querySelector("input[type='file'][name='extra_images']");
  const primaryClear = form.querySelector("[name='image-clear']");
  const removalInputs = Array.from(form.querySelectorAll("[name='remove_extra_images']"));
  const uploadError = form.querySelector("[data-upload-client-error]");

  const hasGroupError = (group) => Boolean(group.querySelector("[role='alert']"));

  const syncDefectControls = ({ clear = false } = {}) => {
    const isPresent = disclosure?.value === "PRESENT";

    if (!isPresent && clear) {
      defectInputs.forEach((input) => {
        input.checked = false;
      });
      if (details) {
        details.value = "";
      }
    }

    dependentGroups.forEach((group) => {
      const visible = isPresent || (!clear && hasGroupError(group));
      group.hidden = !visible;
      group.setAttribute("aria-hidden", String(!visible));
      group.querySelectorAll("input, textarea, select").forEach((control) => {
        control.disabled = !visible;
      });
    });

    const otherChecked = defectInputs.some(
      (input) => input.value === "OTHER" && input.checked,
    );
    if (details) {
      details.required = isPresent && otherChecked;
      details.setAttribute("aria-required", String(details.required));
    }
  };

  disclosure?.addEventListener("change", () => syncDefectControls({ clear: true }));
  defectInputs.forEach((input) => {
    input.addEventListener("change", () => syncDefectControls());
  });
  syncDefectControls();

  const maxFiles = Number(form.dataset.maxFiles || 5);
  const maxFileBytes = Number(form.dataset.maxFileBytes || 5 * 1024 * 1024);
  const maxTotalBytes = Number(form.dataset.maxTotalBytes || 20 * 1024 * 1024);
  const currentPrimary = Number(form.dataset.currentPrimary || 0);
  const currentExtra = Number(form.dataset.currentExtra || 0);

  const syncUploadLimits = () => {
    const primaryFiles = Array.from(primaryInput?.files || []);
    const extraFiles = Array.from(extraInput?.files || []);
    const newFiles = [...primaryFiles, ...extraFiles];
    const removedExtra = removalInputs.filter((input) => input.checked).length;
    const finalPrimary = primaryFiles.length > 0 ? 1 : primaryClear?.checked ? 0 : currentPrimary;
    const finalCount = finalPrimary + currentExtra - removedExtra + extraFiles.length;
    const totalBytes = newFiles.reduce((total, file) => total + file.size, 0);
    const oversizedFile = newFiles.find((file) => file.size > maxFileBytes);

    let message = "";
    if (oversizedFile) {
      message = `${oversizedFile.name} 파일이 장당 5MB 제한을 넘습니다.`;
    } else if (newFiles.length > maxFiles || finalCount > maxFiles) {
      message = `상품 사진은 현재 사진과 새 사진을 합쳐 최대 ${maxFiles}장입니다.`;
    } else if (totalBytes > maxTotalBytes) {
      message = "한 번에 선택한 새 이미지의 합계는 20MB 이하여야 합니다.";
    }

    [primaryInput, extraInput].forEach((input) => {
      input?.setCustomValidity(message);
    });
    if (uploadError) {
      uploadError.textContent = message;
      uploadError.hidden = !message;
    }
  };

  [primaryInput, extraInput, primaryClear, ...removalInputs].forEach((control) => {
    control?.addEventListener("change", syncUploadLimits);
  });
  syncUploadLimits();
})();
