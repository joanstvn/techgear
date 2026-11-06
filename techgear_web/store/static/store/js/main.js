(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasGsap = !!(window.gsap && window.ScrollTrigger && window.ScrollToPlugin);
  var hasFlip = !!window.Flip;
  var hasLenis = typeof window.Lenis === "function";
  var lenis = null;
  var nav = document.querySelector("[data-nav]");
  var backTop = document.querySelector("[data-back-top]");

  if (hasGsap) {
    gsap.registerPlugin(ScrollTrigger, ScrollToPlugin);
    if (hasFlip) gsap.registerPlugin(Flip);
    gsap.config({ nullTargetWarn: false });
  }

  if (hasLenis) {
    lenis = new window.Lenis({
      autoRaf: !hasGsap,
      anchors: false,
      smoothWheel: true,
      respectReducedMotion: true
    });
    window.techgearLenis = lenis;

    if (hasGsap) {
      lenis.on("scroll", ScrollTrigger.update);
      gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
      gsap.ticker.lagSmoothing(0);
    }
  }

  document.documentElement.setAttribute(
    "data-motion-engine",
    hasLenis ? (hasGsap ? "gsap+lenis" : "lenis") : (hasGsap ? "gsap" : "fallback")
  );

  if (hasGsap) {
    /* El navbar vuelve a su cápsula inicial al llegar arriba y se contrae al bajar. */
    if (nav) {
      var flipTargets = nav.querySelectorAll("[data-flip]");
      var navIsStuck = nav.classList.contains("is-stuck");
      var setNavState = function (stuck) {
        if (stuck === navIsStuck) return;
        navIsStuck = stuck;

        var isMobile = window.innerWidth <= 860;
        if (reduceMotion || isMobile || !hasFlip) {
          nav.classList.toggle("is-stuck", navIsStuck);
          return;
        }

        var flipState = Flip.getState(flipTargets, {
          props: "backgroundColor,boxShadow,borderRadius"
        });
        nav.classList.toggle("is-stuck", stuck);
        nav.classList.add("is-flipping");

        var finishFlip = function () { nav.classList.remove("is-flipping"); };
        Flip.from(flipState, {
          duration: 0.95,
          ease: "elastic.out(0.7, 0.55)",
          absolute: true,
          scale: true,
          nested: true,
          onComplete: finishFlip,
          onInterrupt: finishFlip
        });
      };
      setNavState(window.scrollY > 24);
      ScrollTrigger.create({
        start: 24,
        end: 999999,
        onEnter: function () { setNavState(true); },
        onLeaveBack: function () { setNavState(false); }
      });
    }

    if (!reduceMotion) {
      /* Reveals consistentes con ScrollTrigger, sin depender de IntersectionObserver. */
      var revealItems = document.querySelectorAll(".reveal");
      if (revealItems.length) {
        document.documentElement.classList.add("reveal-ready");
        gsap.set(revealItems, { autoAlpha: 0, y: 24 });
        revealItems.forEach(function (item) {
          gsap.to(item, {
            autoAlpha: 1,
            y: 0,
            duration: 0.68,
            ease: "power3.out",
            scrollTrigger: { trigger: item, start: "top 88%", toggleActions: "play none none reverse" }
          });
        });
      }

    } else {
      document.querySelectorAll(".reveal").forEach(function (item) { item.classList.add("is-visible"); });
    }

    if (backTop) {
      var setBackTopState = function (visible) {
        backTop.classList.toggle("is-visible", visible);
      };
      setBackTopState(window.scrollY > 600);
      ScrollTrigger.create({
        start: 600,
        end: 999999,
        onEnter: function () { setBackTopState(true); },
        onLeaveBack: function () { setBackTopState(false); },
        onUpdate: function (self) { setBackTopState(self.scroll() > 600); }
      });
      backTop.addEventListener("click", function () {
        if (lenis) lenis.scrollTo(0, { duration: 0.9, immediate: reduceMotion });
        else if (reduceMotion) window.scrollTo({ top: 0, behavior: "auto" });
        else gsap.to(window, { duration: 0.85, scrollTo: { y: 0, autoKill: true }, ease: "power2.inOut", overwrite: "auto" });
      });
    }

    window.addEventListener("load", function () { ScrollTrigger.refresh(); }, { once: true });
  } else {
    /* Fallback si GSAP no está disponible: conserva el comportamiento esencial. */
    if (nav) {
      var onScroll = function () { nav.classList.toggle("is-stuck", window.scrollY > 24); };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    }
    var reveals = document.querySelectorAll(".reveal");
    if (reveals.length && !reduceMotion && "IntersectionObserver" in window) {
      document.documentElement.classList.add("reveal-ready");
      var revealObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
      reveals.forEach(function (item) { revealObserver.observe(item); });
    } else {
      reveals.forEach(function (item) { item.classList.add("is-visible"); });
    }
    if (backTop) {
      var toggleBackTop = function () { backTop.classList.toggle("is-visible", window.scrollY > 600); };
      window.addEventListener("scroll", toggleBackTop, { passive: true });
      toggleBackTop();
      backTop.addEventListener("click", function () {
        if (lenis) lenis.scrollTo(0, { duration: 0.9, immediate: reduceMotion });
        else window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
      });
    }
  }

  /* Activa la prestación que cruza la zona de lectura, igual con o sin GSAP. */
  (function initScrollHighlight() {
    var section = document.querySelector(".scroll-hl");
    var items = section ? Array.prototype.slice.call(section.querySelectorAll(".scroll-hl__item")) : [];
    if (!section || !items.length) return;

    var framePending = false;
    var activeIndex = items.findIndex(function (item) { return item.classList.contains("is-active"); });
    if (activeIndex < 0) activeIndex = 0;
    var desiredIndex = activeIndex;
    var transitionTimer = null;

    var applyActiveIndex = function (index) {
      activeIndex = Math.max(0, Math.min(index, items.length - 1));
      items.forEach(function (item, itemIndex) {
        var active = itemIndex === activeIndex;
        item.classList.toggle("is-active", active);
        if (active) item.setAttribute("aria-current", "true");
        else item.removeAttribute("aria-current");
      });
    };

    var advanceTowardDesired = function () {
      transitionTimer = null;
      if (activeIndex === desiredIndex) return;
      applyActiveIndex(activeIndex + (desiredIndex > activeIndex ? 1 : -1));
      if (activeIndex !== desiredIndex) transitionTimer = window.setTimeout(advanceTowardDesired, 170);
    };

    var requestActiveIndex = function (index, immediate) {
      desiredIndex = Math.max(0, Math.min(index, items.length - 1));
      if (immediate || reduceMotion) {
        window.clearTimeout(transitionTimer);
        transitionTimer = null;
        applyActiveIndex(desiredIndex);
      } else if (activeIndex === desiredIndex) {
        window.clearTimeout(transitionTimer);
        transitionTimer = null;
      } else if (!transitionTimer) {
        if (Math.abs(desiredIndex - activeIndex) === 1) applyActiveIndex(desiredIndex);
        else transitionTimer = window.setTimeout(advanceTowardDesired, 100);
      }
    };

    var updateActiveItem = function () {
      framePending = false;
      var focusLine = Math.min(Math.max(window.innerHeight * 0.3, 190), window.innerHeight * 0.42);
      var sectionRect = section.getBoundingClientRect();
      if (sectionRect.top > focusLine) {
        requestActiveIndex(0, true);
        return;
      }
      if (sectionRect.bottom < focusLine) {
        requestActiveIndex(items.length - 1, true);
        return;
      }

      var closestIndex = 0;
      var closestDistance = Infinity;
      items.forEach(function (item, index) {
        var rect = item.getBoundingClientRect();
        var distance = Math.abs(rect.top + rect.height / 2 - focusLine);
        if (distance < closestDistance) {
          closestDistance = distance;
          closestIndex = index;
        }
      });

      var referenceIndex = transitionTimer ? desiredIndex : activeIndex;
      var referenceRect = items[referenceIndex].getBoundingClientRect();
      var referenceDistance = Math.abs(referenceRect.top + referenceRect.height / 2 - focusLine);
      // Evita invertir el destino cuando la línea de lectura queda entre dos filas.
      if (closestIndex !== referenceIndex && closestDistance + 24 >= referenceDistance) closestIndex = referenceIndex;
      requestActiveIndex(closestIndex, false);
    };
    var scheduleUpdate = function () {
      if (framePending) return;
      framePending = true;
      window.requestAnimationFrame(updateActiveItem);
    };

    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);
    window.addEventListener("load", scheduleUpdate, { once: true });
    if (lenis) lenis.on("scroll", scheduleUpdate);
    scheduleUpdate();
  })();

  /* Desplaza con Lenis todos los anclajes de la página y respeta el navbar fijo. */
  document.addEventListener("click", function (event) {
    var link = event.target.closest('a[href*="#"]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var url;
    try { url = new URL(link.href, window.location.href); } catch (error) { return; }
    var samePage = url.origin === window.location.origin && url.pathname.replace(/\/$/, "") === window.location.pathname.replace(/\/$/, "");
    if (!samePage || !url.hash || url.hash === "#") return;
    var target = document.getElementById(decodeURIComponent(url.hash.slice(1)));
    if (!target) return;
    event.preventDefault();
    if (lenis) {
      lenis.scrollTo(target, {
        offset: -(nav ? nav.offsetHeight : 0) - 18,
        duration: 1.05,
        immediate: reduceMotion,
        onComplete: function () { history.replaceState(null, "", url.hash); }
      });
    } else if (hasGsap && !reduceMotion) {
      gsap.to(window, {
        duration: 0.9,
        scrollTo: { y: target, offsetY: (nav ? nav.offsetHeight : 0) + 18, autoKill: true },
        ease: "power2.inOut",
        overwrite: "auto",
        onComplete: function () { history.replaceState(null, "", url.hash); }
      });
    } else {
      target.scrollIntoView({ block: "start", behavior: "auto" });
      history.replaceState(null, "", url.hash);
    }
  });

  /* Alertas: cierre manual y auto-descarte. */
  document.querySelectorAll("[data-dismiss]").forEach(function (button) {
    button.addEventListener("click", function () {
      var alert = button.closest(".alert");
      if (alert) alert.remove();
    });
  });
  window.setTimeout(function () {
    document.querySelectorAll(".messages .alert").forEach(function (alert) {
      if (window.gsap) gsap.to(alert, { autoAlpha: 0, y: -6, duration: 0.4, onComplete: function () { alert.remove(); } });
      else {
        alert.style.transition = "opacity .4s ease, transform .4s ease";
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-6px)";
        window.setTimeout(function () { alert.remove(); }, 420);
      }
    });
  }, 6500);

  document.querySelectorAll("[data-order-form]").forEach(function (form) {
    var quantity = form.querySelector("[data-order-quantity]");
    var total = form.querySelector("[data-order-total]");
    var unitPrice = Number(form.getAttribute("data-unit-price"));
    if (!quantity || !total || !Number.isFinite(unitPrice)) return;
    var quantityControl = quantity.closest("[data-quantity-control]");
    var stepButtons = quantityControl ? quantityControl.querySelectorAll("[data-quantity-step]") : [];

    var updateEstimatedTotal = function () {
      var minimum = Number(quantity.min) || 1;
      var units = Math.max(minimum, Number(quantity.value) || minimum);
      var maximum = Number(quantity.max);
      if (maximum > 0) units = Math.min(units, maximum);
      stepButtons.forEach(function (button) {
        var step = Number(button.getAttribute("data-quantity-step"));
        button.disabled = (step < 0 && units <= minimum) || (step > 0 && maximum > 0 && units >= maximum);
      });
      var formatted = new Intl.NumberFormat("es-CO", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(unitPrice * units);
      total.textContent = "$" + formatted + " COP";
    };

    quantity.addEventListener("input", updateEstimatedTotal);
    stepButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        var step = Number(button.getAttribute("data-quantity-step"));
        var current = Number(quantity.value) || Number(quantity.min) || 1;
        var next = current + step;
        var maximum = Number(quantity.max);
        quantity.value = String(Math.max(Number(quantity.min) || 1, maximum > 0 ? Math.min(next, maximum) : next));
        quantity.dispatchEvent(new Event("input", { bubbles: true }));
      });
    });
    updateEstimatedTotal();
  });
})();
