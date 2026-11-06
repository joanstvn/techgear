(() => {
  const productModal = document.getElementById("product-modal");
  const deleteModal = document.getElementById("delete-modal");
  const userModal = document.getElementById("user-modal");
  const userDeleteModal = document.getElementById("user-delete-modal");
  if (!productModal || !deleteModal || !userModal || !userDeleteModal) return;

  const enhancedSelects = new WeakMap();
  const syncEnhancedSelect = (select) => {
    const control = enhancedSelects.get(select);
    if (!control) return;
    const selectedIndex = Math.max(0, select.selectedIndex);
    const selectedOption = select.options[selectedIndex];
    control.trigger.textContent = selectedOption?.textContent.trim() || "Seleccionar";
    if (select.closest(".admin-order-status-form")) {
      control.trigger.dataset.status = selectedOption?.value || "";
    }
    control.options.forEach((optionButton, index) => {
      const selected = index === selectedIndex;
      optionButton.setAttribute("aria-selected", String(selected));
      optionButton.classList.toggle("is-selected", selected);
    });
  };
  const enhanceSelect = (select, index) => {
    const wrapper = document.createElement("div");
    wrapper.className = `admin-select-control${select.closest(".admin-order-status-form") ? " admin-order-select-control" : ""}`;
    const listId = `admin-select-list-${index}`;
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "admin-select-trigger";
    trigger.setAttribute("role", "combobox");
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-controls", listId);
    trigger.setAttribute("aria-label", select.labels?.[0]?.textContent.trim() || select.closest(".admin-field")?.childNodes[0]?.textContent.trim() || "Seleccionar opción");
    const list = document.createElement("div");
    list.className = "admin-select-list";
    list.id = listId;
    list.setAttribute("role", "listbox");
    list.hidden = true;
    const optionButtons = [...select.options].map((option) => {
      const optionButton = document.createElement("button");
      optionButton.type = "button";
      optionButton.className = "admin-select-option";
      optionButton.setAttribute("role", "option");
      if (select.closest(".admin-order-status-form")) optionButton.dataset.status = option.value;
      optionButton.textContent = option.textContent.trim();
      optionButton.addEventListener("click", () => {
        select.value = option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        syncEnhancedSelect(select);
        list.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        trigger.focus();
      });
      optionButton.addEventListener("mousemove", () => {
        optionButtons.forEach((button) => button.classList.remove("is-active"));
        optionButton.classList.add("is-active");
      });
      list.append(optionButton);
      return optionButton;
    });
    wrapper.append(trigger, list);
    select.after(wrapper);
    select.classList.add("admin-select-native");
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");
    enhancedSelects.set(select, { trigger, list, options: optionButtons });

    const closeList = (returnFocus = false) => {
      list.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      if (returnFocus) trigger.focus();
    };
    const openList = () => {
      list.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      optionButtons.forEach((button) => button.classList.remove("is-active"));
      optionButtons[select.selectedIndex]?.classList.add("is-active");
    };
    trigger.addEventListener("click", () => list.hidden ? openList() : closeList());
    trigger.addEventListener("keydown", (event) => {
      const isOpen = !list.hidden;
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
        event.preventDefault();
        if (!isOpen) openList();
        else if (event.key === "Enter" || event.key === " ") {
          const activeOption = optionButtons.find((button) => button.classList.contains("is-active"));
          activeOption?.click();
        }
        else {
          const activeIndex = Math.max(0, optionButtons.findIndex((button) => button.classList.contains("is-active")));
          const nextIndex = event.key === "ArrowUp"
            ? (activeIndex + optionButtons.length - 1) % optionButtons.length
            : (activeIndex + 1) % optionButtons.length;
          optionButtons.forEach((button) => button.classList.remove("is-active"));
          optionButtons[nextIndex]?.classList.add("is-active");
          optionButtons[nextIndex]?.scrollIntoView({ block: "nearest" });
        }
      } else if (event.key === "Escape" && isOpen) {
        event.preventDefault();
        closeList(true);
      } else if (event.key === "Home" || event.key === "End") {
        event.preventDefault();
        openList();
        optionButtons.forEach((button) => button.classList.remove("is-active"));
        optionButtons[event.key === "Home" ? 0 : optionButtons.length - 1]?.classList.add("is-active");
      }
    });
    list.addEventListener("keydown", (event) => {
      const activeIndex = Math.max(0, optionButtons.findIndex((button) => button.classList.contains("is-active")));
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? optionButtons.length - 1 : (activeIndex + (event.key === "ArrowDown" ? 1 : optionButtons.length - 1)) % optionButtons.length;
        optionButtons.forEach((button) => button.classList.remove("is-active"));
        optionButtons[nextIndex]?.classList.add("is-active");
        optionButtons[nextIndex]?.focus();
      } else if (event.key === "Escape") closeList(true);
    });
    list.addEventListener("focusout", (event) => {
      if (!list.contains(event.relatedTarget) && event.relatedTarget !== trigger) closeList();
    });
    select.addEventListener("change", () => syncEnhancedSelect(select));
    select.form?.addEventListener("reset", () => requestAnimationFrame(() => syncEnhancedSelect(select)));
    document.addEventListener("pointerdown", (event) => {
      if (!wrapper.contains(event.target)) closeList();
    });
    syncEnhancedSelect(select);
  };
  document.querySelectorAll(".admin-modal .admin-field select, .admin-order-status-form select").forEach(enhanceSelect);

  const adminTabs = [...document.querySelectorAll("[data-admin-tab]")];
  const adminTablist = document.querySelector(".admin-sidebar__pills");
  const mobileAdminTabs = window.matchMedia("(max-width: 680px)");
  const syncAdminTabOrientation = () => {
    adminTablist?.setAttribute("aria-orientation", mobileAdminTabs.matches ? "horizontal" : "vertical");
  };
  syncAdminTabOrientation();
  mobileAdminTabs.addEventListener("change", syncAdminTabOrientation);
  const adminPanels = {
    dashboard: document.getElementById("panel-dashboard"),
    products: document.getElementById("panel-products"),
    users: document.getElementById("panel-users"),
    orders: document.getElementById("panel-orders"),
  };
  const activateAdminTab = (selectedTab, moveFocus = false) => {
    const selectedName = selectedTab.dataset.adminTab;
    adminTabs.forEach((tab) => {
      const isSelected = tab === selectedTab;
      tab.classList.toggle("is-active", isSelected);
      tab.setAttribute("aria-selected", String(isSelected));
      tab.tabIndex = isSelected ? 0 : -1;
    });
    Object.entries(adminPanels).forEach(([name, panel]) => { panel.hidden = name !== selectedName; });
    document.querySelectorAll("[data-tab-action]").forEach((action) => {
      action.hidden = action.dataset.tabAction !== selectedName;
    });
    const currentUrl = new URL(window.location.href);
    if (selectedName === "dashboard") currentUrl.searchParams.delete("section");
    else currentUrl.searchParams.set("section", selectedName);
    window.history.replaceState(window.history.state, "", `${currentUrl.pathname}${currentUrl.search}${currentUrl.hash}`);
    if (moveFocus) selectedTab.focus();
  };
  adminTabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateAdminTab(tab));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? adminTabs.length - 1 : (index + (["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : adminTabs.length - 1)) % adminTabs.length;
      activateAdminTab(adminTabs[nextIndex], true);
    });
  });
  const requestedAdminSection = new URLSearchParams(window.location.search).get("section");
  const requestedAdminTab = adminTabs.find((tab) => tab.dataset.adminTab === requestedAdminSection);
  if (requestedAdminTab) activateAdminTab(requestedAdminTab);

  const adminScrollStorageKey = "techgear-admin-orders-scroll";
  document.querySelectorAll("[data-admin-preserve-position]").forEach((form) => {
    form.addEventListener("submit", () => {
      try {
        sessionStorage.setItem(adminScrollStorageKey, JSON.stringify({
          page: window.scrollY,
          list: document.querySelector(".admin-order-list")?.scrollTop || 0,
        }));
      } catch (_) {}
    });
  });
  try {
    const savedScroll = sessionStorage.getItem(adminScrollStorageKey);
    if (savedScroll) {
      sessionStorage.removeItem(adminScrollStorageKey);
      const position = JSON.parse(savedScroll);
      requestAnimationFrame(() => {
        const orderList = document.querySelector(".admin-order-list");
        if (orderList) orderList.scrollTop = Number(position.list) || 0;
        window.scrollTo(0, Number(position.page) || 0);
      });
    }
  } catch (_) {}

  const productForm = document.getElementById("product-form");
  const productTitle = document.getElementById("product-modal-title");
  const productSubmit = productForm.querySelector('[type="submit"]');
  const productCreateAction = productForm.action;
  const productFields = ["name", "category", "price", "stock", "description"];
  const clearFieldError = (field) => {
    field.closest(".admin-field")?.classList.remove("is-invalid");
    field.removeAttribute("aria-invalid");
  };
  const setupRequiredValidation = (form) => {
    form.addEventListener("reset", () => {
      form.querySelectorAll("[aria-invalid='true']").forEach(clearFieldError);
    });
    form.addEventListener("input", (event) => {
      const field = event.target;
      if (field.matches("[required]") && field.value.trim() && field.validity.valid) clearFieldError(field);
    });
    form.addEventListener("change", (event) => {
      const field = event.target;
      if (field.matches("[required]") && field.value.trim() && field.validity.valid) clearFieldError(field);
    });
    form.addEventListener("submit", (event) => {
      const invalidFields = [...form.querySelectorAll("[required]")].filter((field) => (
        !field.value.trim() || !field.validity.valid
      ));
      form.querySelectorAll("[aria-invalid='true']").forEach(clearFieldError);
      if (!invalidFields.length) return;

      event.preventDefault();
      invalidFields.forEach((field) => {
        const container = field.closest(".admin-field");
        container?.classList.add("is-invalid");
        field.setAttribute("aria-invalid", "true");
        if (container) {
          container.classList.remove("is-invalid");
          void container.offsetWidth;
          container.classList.add("is-invalid");
        }
      });
      const invalidControl = invalidFields[0];
      (enhancedSelects.get(invalidControl)?.trigger || invalidControl).focus({ preventScroll: true });
    });
  };
  setupRequiredValidation(productForm);
  const fieldFor = (form, name) => form.elements.namedItem(name);
  const imageFileField = fieldFor(productForm, "image_file");
  const imageUrlField = fieldFor(productForm, "image_url");
  const imageSourceContainer = productForm.querySelector("[data-image-source]");
  const imageFileName = productForm.querySelector("[data-file-name]");
  const clearImageSourceError = () => {
    imageSourceContainer.classList.remove("is-invalid");
    imageSourceContainer.querySelectorAll(".admin-field").forEach((field) => field.classList.remove("is-invalid"));
    [imageFileField, imageUrlField].forEach((field) => field.removeAttribute("aria-invalid"));
  };
  imageFileField.addEventListener("change", () => {
    imageFileName.textContent = imageFileField.files[0]?.name || "Ningún archivo seleccionado";
    if (imageFileField.files.length) imageUrlField.value = "";
    if (imageFileField.files.length || imageUrlField.value.trim()) clearImageSourceError();
  });
  imageUrlField.addEventListener("input", () => {
    if (imageUrlField.value.trim()) imageFileField.value = "";
    if (imageUrlField.value.trim() && imageUrlField.validity.valid) clearImageSourceError();
  });
  productForm.addEventListener("reset", clearImageSourceError);
  productForm.addEventListener("submit", (event) => {
    const hasFile = imageFileField.files.length > 0;
    const hasUrl = Boolean(imageUrlField.value.trim());
    const rawUrl = imageUrlField.value.trim();
    const isLegacyStaticPath = rawUrl.startsWith("/static/");
    let isPublicImageUrl = false;
    try {
      const parsedUrl = new URL(rawUrl);
      isPublicImageUrl = parsedUrl.protocol === "https:" || parsedUrl.protocol === "http:";
    } catch (_) {}
    const invalidImageSource = hasFile === hasUrl || (hasUrl && !isPublicImageUrl && !isLegacyStaticPath);
    if (!invalidImageSource) return;

    event.preventDefault();
    imageSourceContainer.classList.remove("is-invalid");
    void imageSourceContainer.offsetWidth;
    imageSourceContainer.classList.add("is-invalid");
    const fieldToFocus = hasUrl ? imageUrlField : imageFileField;
    fieldToFocus.setAttribute("aria-invalid", "true");
    fieldToFocus.closest(".admin-field")?.classList.add("is-invalid");
    fieldToFocus.focus({ preventScroll: true });
  });

  document.querySelectorAll("[data-open-product]").forEach((button) => button.addEventListener("click", () => {
    productForm.reset();
    imageFileName.textContent = "Ningún archivo seleccionado";
    productForm.action = productCreateAction;
    productTitle.textContent = "Añadir producto";
    productSubmit.textContent = "Guardar producto";
    productModal.showModal();
  }));

  document.querySelectorAll("[data-edit-product]").forEach((button) => button.addEventListener("click", () => {
    productForm.reset();
    imageFileName.textContent = "Ningún archivo seleccionado";
    productTitle.textContent = "Editar producto";
    productSubmit.textContent = "Guardar cambios";
    productForm.action = `/administracion/productos/${encodeURIComponent(button.dataset.id)}/editar/`;
    productFields.forEach((name) => { fieldFor(productForm, name).value = button.dataset[name] || ""; });
    productForm.querySelectorAll("select").forEach(syncEnhancedSelect);
    imageUrlField.value = button.dataset.image || "";
    productModal.showModal();
  }));

  const deleteForm = document.getElementById("delete-form");
  document.querySelectorAll("[data-delete-product]").forEach((button) => button.addEventListener("click", () => {
    deleteForm.action = `/administracion/productos/${encodeURIComponent(button.dataset.id)}/eliminar/`;
    deleteModal.querySelector("[data-delete-name]").textContent = button.dataset.name || "este producto";
    deleteModal.showModal();
  }));

  const userForm = document.getElementById("user-form");
  const userTitle = document.getElementById("user-modal-title");
  const userSubmit = userForm.querySelector('[type="submit"]');
  const userPassword = fieldFor(userForm, "password");
  const userCreateAction = userForm.action;
  setupRequiredValidation(userForm);
  document.querySelectorAll("[data-open-user]").forEach((button) => button.addEventListener("click", () => {
    userForm.reset();
    userForm.action = userCreateAction;
    userTitle.textContent = "Añadir usuario";
    userSubmit.textContent = "Crear usuario";
    userPassword.required = true;
    userForm.querySelector("[data-password-hint]").textContent = "Usa al menos 12 caracteres.";
    fieldFor(userForm, "role").value = "cliente";
    userForm.querySelectorAll("select").forEach(syncEnhancedSelect);
    userModal.showModal();
  }));

  document.querySelectorAll("[data-edit-user]").forEach((button) => button.addEventListener("click", () => {
    userForm.reset();
    userForm.action = `/administracion/usuarios/${encodeURIComponent(button.dataset.id)}/editar/`;
    fieldFor(userForm, "full_name").value = button.dataset.name || "";
    fieldFor(userForm, "username").value = button.dataset.username || "";
    fieldFor(userForm, "email").value = button.dataset.email || "";
    fieldFor(userForm, "role").value = button.dataset.role === "admin" ? "administrador" : (button.dataset.role || "cliente");
    userForm.querySelectorAll("select").forEach(syncEnhancedSelect);
    userPassword.value = "";
    userPassword.required = false;
    userTitle.textContent = "Editar usuario";
    userSubmit.textContent = "Guardar cambios";
    userForm.querySelector("[data-password-hint]").textContent = "Déjala vacía si no deseas cambiarla; usa 12 caracteres si la cambias.";
    userModal.showModal();
  }));

  const userDeleteForm = document.getElementById("user-delete-form");
  document.querySelectorAll("[data-delete-user]:not(:disabled)").forEach((button) => button.addEventListener("click", () => {
    userDeleteForm.action = `/administracion/usuarios/${encodeURIComponent(button.dataset.id)}/eliminar/`;
    userDeleteModal.querySelector("[data-user-delete-name]").textContent = button.dataset.name || "este usuario";
    userDeleteModal.showModal();
  }));

  document.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
  [productModal, deleteModal, userModal, userDeleteModal].forEach((dialog) => dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  }));
})();
