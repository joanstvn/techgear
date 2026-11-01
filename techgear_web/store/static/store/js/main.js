(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasGsap = !!(window.gsap && window.ScrollTrigger && window.ScrollToPlugin);
  var hasFlip = !!window.Flip;
  var hasLenis = typeof window.Lenis === "function";
  var lenis = null;
  var nav = document.querySelector("[data-nav]");
  var backTop = document.querySelector("[data-back-top]");
  var adminSidebarNav = document.querySelector("[data-admin-sidebar-nav]");

  if (adminSidebarNav) {
    var adminSidebarLinks = Array.prototype.slice.call(adminSidebarNav.querySelectorAll("a"));
    var activeSidebarLink = adminSidebarNav.querySelector("a.active") || adminSidebarLinks[0];
    var indicatorTimeout;

    var moveSidebarIndicator = function (link) {
      if (!link) return;
      adminSidebarNav.style.setProperty("--sidebar-pill-x", link.offsetLeft + "px");
      adminSidebarNav.style.setProperty("--sidebar-pill-y", link.offsetTop + "px");
      adminSidebarNav.style.setProperty("--sidebar-pill-width", link.offsetWidth + "px");
      adminSidebarNav.style.setProperty("--sidebar-pill-height", link.offsetHeight + "px");
    };

    window.requestAnimationFrame(function () { moveSidebarIndicator(activeSidebarLink); });
    adminSidebarLinks.forEach(function (link) {
      link.addEventListener("pointerenter", function () { moveSidebarIndicator(link); });
      link.addEventListener("focus", function () { moveSidebarIndicator(link); });
      link.addEventListener("pointerdown", function () {
        moveSidebarIndicator(link);
        adminSidebarNav.classList.add("is-pressing");
        window.clearTimeout(indicatorTimeout);
      });
    });
    adminSidebarNav.addEventListener("pointerleave", function () {
      adminSidebarNav.classList.remove("is-pressing");
      moveSidebarIndicator(activeSidebarLink);
    });
    adminSidebarNav.addEventListener("focusout", function (event) {
      if (!adminSidebarNav.contains(event.relatedTarget)) moveSidebarIndicator(activeSidebarLink);
    });
    window.addEventListener("pointerup", function () {
      indicatorTimeout = window.setTimeout(function () {
        adminSidebarNav.classList.remove("is-pressing");
      }, 130);
    });
    window.addEventListener("resize", function () { moveSidebarIndicator(activeSidebarLink); });
  }

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
          props: "backgroundColor,boxShadow"
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
      /* Entrada del hero y movimiento leve del robot ligado al scroll. */
      var heroItems = document.querySelectorAll(
        ".hero__eyebrow, .hero__name, .hero__lead, .hero__actions"
      );
      if (heroItems.length) {
        gsap.fromTo(heroItems,
          { autoAlpha: 0, y: 24 },
          { autoAlpha: 1, y: 0, duration: 0.72, stagger: 0.1, ease: "power3.out", delay: 0.12 }
        );
      }
      var robot = document.querySelector(".hero__robot");
      if (robot) {
        gsap.fromTo(robot,
          { autoAlpha: 0, y: 28, scale: 0.94 },
          { autoAlpha: 1, y: 0, scale: 1, duration: 1, delay: 0.25, ease: "power3.out" }
        );
        gsap.to(robot, { y: -9, rotation: 1, duration: 3.2, repeat: -1, yoyo: true, ease: "sine.inOut", delay: 1.3 });
        var heroVisual = document.querySelector(".hero__visual");
        if (heroVisual) {
          gsap.to(heroVisual, {
            y: 48,
            ease: "none",
            scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: 0.6 }
          });
        }
      }

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

  /* ── Hero Gallery: carrusel 3D cóncavo (Reelmark style) con auto-scroll fluido + arrastre suave ── */
  (function initHeroGallery() {
    var gallery = document.querySelector(".hero__gallery");
    var track   = gallery && gallery.querySelector(".hero__gallery-track");
    if (!gallery || !track) return;

    if (window.matchMedia("(max-width: 860px)").matches) {
      gallery.classList.add("is-mobile-carousel");
      var mobileSlides = Array.prototype.slice.call(track.querySelectorAll(".hero__tile"));
      var mobileSlideCount = mobileSlides.length;
      var firstSlideClone = mobileSlides[0] && mobileSlides[0].cloneNode(true);
      if (firstSlideClone) {
        firstSlideClone.setAttribute("aria-hidden", "true");
        firstSlideClone.setAttribute("tabindex", "-1");
        firstSlideClone.classList.add("hero__tile--clone");
        var cloneImage = firstSlideClone.querySelector("img");
        if (cloneImage) cloneImage.alt = "";
        track.appendChild(firstSlideClone);
      }

      var currentMobileSlide = 0;
      var autoplayTimer = null;
      var settleTimer = null;
      var pointerStartX = 0;
      var scrollStartX = 0;
      var mouseDragging = false;
      var dragMoved = false;

      var stopAutoplay = function () { window.clearTimeout(autoplayTimer); };
      var getMobileSlideOffset = function (index) {
        var slide = track.children[index];
        var firstSlide = track.children[0];
        return slide && firstSlide ? slide.offsetLeft - firstSlide.offsetLeft : 0;
      };
      var startAutoplay = function () {
        stopAutoplay();
        autoplayTimer = window.setTimeout(function () {
          currentMobileSlide += 1;
          gallery.scrollTo({ left: getMobileSlideOffset(currentMobileSlide), behavior: "smooth" });
        }, 3600);
      };
      var returnToFirstSlide = function () {
        gallery.style.scrollBehavior = "auto";
        gallery.scrollLeft = 0;
        currentMobileSlide = 0;
        window.requestAnimationFrame(function () {
          gallery.style.scrollBehavior = "";
          startAutoplay();
        });
      };

      gallery.addEventListener("scroll", function () {
        window.clearTimeout(settleTimer);
        settleTimer = window.setTimeout(function () {
          var nextSlide = 0;
          var closestDistance = Infinity;
          Array.prototype.forEach.call(track.children, function (slide, index) {
            var distance = Math.abs(gallery.scrollLeft - getMobileSlideOffset(index));
            if (distance < closestDistance) {
              closestDistance = distance;
              nextSlide = index;
            }
          });
          if (nextSlide >= mobileSlideCount) {
            returnToFirstSlide();
            return;
          }
          currentMobileSlide = Math.max(0, Math.min(nextSlide, mobileSlideCount - 1));
          startAutoplay();
        }, 180);
      }, { passive: true });

      gallery.addEventListener("pointerdown", function (event) {
        stopAutoplay();
        if (event.pointerType !== "mouse" || event.button !== 0) return;
        mouseDragging = true;
        dragMoved = false;
        pointerStartX = event.clientX;
        scrollStartX = gallery.scrollLeft;
        gallery.classList.add("is-dragging");
        gallery.setPointerCapture(event.pointerId);
      });
      gallery.addEventListener("pointermove", function (event) {
        if (!mouseDragging) return;
        var distance = event.clientX - pointerStartX;
        if (Math.abs(distance) > 5) dragMoved = true;
        if (dragMoved) {
          gallery.scrollLeft = scrollStartX - distance;
          event.preventDefault();
        }
      });
      var finishMouseDrag = function () {
        if (mouseDragging) {
          mouseDragging = false;
          gallery.classList.remove("is-dragging");
        }
        window.setTimeout(startAutoplay, 500);
      };
      gallery.addEventListener("pointerup", finishMouseDrag);
      gallery.addEventListener("pointercancel", finishMouseDrag);
      gallery.addEventListener("click", function (event) {
        if (!dragMoved) return;
        event.preventDefault();
        event.stopPropagation();
        dragMoved = false;
      }, true);
      gallery.addEventListener("dragstart", function (event) { event.preventDefault(); });
      startAutoplay();
      return;
    }

    /* Triplicar los tiles para un buffer continuo a cualquier ancho de pantalla */
    var originalHTML = track.innerHTML;
    track.innerHTML = originalHTML + originalHTML + originalHTML;

    var tiles         = Array.prototype.slice.call(track.querySelectorAll(".hero__tile"));
    var totalTiles    = tiles.length;
    var originalCount = 9;

    var speed         = 0.35;  /* Velocidad de auto-scroll lenta y fluida (px/frame) */
    var autoX         = 0;     /* Offset acumulado del auto-scroll */
    var dragX         = 0;     /* Offset acumulado del arrastre */
    var dragging      = false;
    var startPointerX = 0;
    var startDragX    = 0;
    var velocity      = 0;
    var lastPointerX  = 0;
    var lastTime      = 0;
    var dragMoved     = false;

    var galleryWidth   = gallery.offsetWidth;
    var centerX        = galleryWidth * 0.5;
    var halfWidth      = galleryWidth * 0.5;
    var tileOffsets    = [];
    var tileBaseWidth  = 225;
    var singleSetWidth = 0;

    function measure() {
      galleryWidth = gallery.offsetWidth;
      centerX      = galleryWidth * 0.5;
      halfWidth    = galleryWidth * 0.5;

      /* Medir offsets reales limpios de cada tile dentro del track */
      track.style.transform = "none";
      tileOffsets = [];
      for (var i = 0; i < totalTiles; i++) {
        tiles[i].style.transform = "none";
        tileOffsets.push(tiles[i].offsetLeft);
      }

      var firstTile = tiles[0];
      tileBaseWidth = firstTile ? firstTile.offsetWidth : 225;

      if (totalTiles >= originalCount * 2 && tileOffsets[originalCount] !== undefined) {
        singleSetWidth = tileOffsets[originalCount] - tileOffsets[0];
      } else {
        singleSetWidth = (tileBaseWidth + 18) * originalCount;
      }
    }

    measure();
    window.addEventListener("resize", measure);

    /* Actualiza la perspectiva cóncava individual de cada tarjeta según su posición en pantalla */
    function updateTiles3D(totalX) {
      var halfTile = tileBaseWidth * 0.5;
      for (var i = 0; i < totalTiles; i++) {
        var tileCenterInGallery = totalX + tileOffsets[i] + halfTile;
        var normX = (tileCenterInGallery - centerX) / halfWidth;

        // Si está completamente fuera de la vista más margen de bleed, ocultar
        if (normX < -1.4 || normX > 1.4) {
          tiles[i].style.opacity = "0";
          continue;
        }

        tiles[i].style.opacity = "1";
        var absX   = Math.abs(normX);
        var factor = Math.min(Math.pow(absX, 1.3), 1.25);

        /*
          Curva idéntica a la referencia (Reelmark):
          - Tarjetas más grandes y anchas con espacio uniforme y compacto (gap: 18px).
          - Altura cóncava: scaleY de 0.86 (centro) a 1.12 (bordes).
          - Ancho estable: scaleX de 0.98 a 1.01 para que la separación entre tarjetas sea constante y limpia.
          - Inclinación sutil hacia el centro: rotateY ±6.0°.
        */
        var scaleX  = 0.98 + 0.03 * factor;
        var scaleY  = 0.86 + 0.26 * factor;
        var rotateY = -normX * 6.0;

        tiles[i].style.transform =
          "perspective(1200px) rotateY(" + rotateY.toFixed(2) + "deg) scale(" + scaleX.toFixed(3) + ", " + scaleY.toFixed(3) + ")";
      }
    }

    function loop() {
      if (!dragging) {
        /* Desaceleración suave del impulso de arrastre */
        if (Math.abs(velocity) > 0.05) {
          dragX += velocity;
          velocity *= 0.94;
        } else {
          velocity = 0;
        }

        autoX -= speed;
      }

      var totalX = autoX + dragX;

      /* Bucle infinito sin saltos */
      if (singleSetWidth > 0) {
        while (totalX < -singleSetWidth) {
          autoX += singleSetWidth;
          totalX = autoX + dragX;
        }
        while (totalX > 0) {
          autoX -= singleSetWidth;
          totalX = autoX + dragX;
        }
      }

      track.style.transform = "translate3d(" + totalX.toFixed(2) + "px, 0, 0)";
      updateTiles3D(totalX);

      requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);

    /* ── Arrastre suave (mouse + touch) ── */
    function pointerDown(e) {
      dragging      = true;
      dragMoved     = false;
      velocity      = 0;
      gallery.classList.add("is-dragging");

      var clientX   = e.touches ? e.touches[0].clientX : e.clientX;
      startPointerX = clientX;
      startDragX    = dragX;
      lastPointerX  = clientX;
      lastTime      = Date.now();
    }

    function pointerMove(e) {
      if (!dragging) return;
      var clientX = e.touches ? e.touches[0].clientX : e.clientX;
      var now     = Date.now();
      var dt      = Math.max(now - lastTime, 1);

      if (Math.abs(clientX - startPointerX) > 5) {
        dragMoved = true;
      }

      dragX = startDragX + (clientX - startPointerX);

      /* Suavizado de velocidad para inercia fluida al soltar */
      var currentVel = ((clientX - lastPointerX) / dt) * 16;
      velocity = velocity * 0.3 + currentVel * 0.7;
      lastPointerX = clientX;
      lastTime     = now;

      if (e.cancelable) e.preventDefault();
    }

    function pointerUp() {
      if (!dragging) return;
      dragging = false;
      gallery.classList.remove("is-dragging");
      if (velocity > 24) velocity = 24;
      if (velocity < -24) velocity = -24;
    }

    gallery.addEventListener("mousedown",  pointerDown);
    window.addEventListener("mousemove",   pointerMove);
    window.addEventListener("mouseup",     pointerUp);

    gallery.addEventListener("touchstart", pointerDown, { passive: true });
    window.addEventListener("touchmove",   pointerMove, { passive: false });
    window.addEventListener("touchend",    pointerUp);
    window.addEventListener("touchcancel", pointerUp);

    /* Evitar que los clicks naveguen mientras se arrastra */
    gallery.addEventListener("click", function (e) {
      if (dragMoved) {
        e.preventDefault();
        e.stopPropagation();
      }
    }, true);

    /* Evitar arrastre nativo de imágenes del navegador */
    gallery.addEventListener("dragstart", function (e) { e.preventDefault(); });
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

  /* Mostrar u ocultar contraseña. */
  document.querySelectorAll("[data-toggle-password]").forEach(function (passwordToggle) {
    passwordToggle.addEventListener("click", function () {
      var wrap = passwordToggle.closest(".auth__input-wrap");
      var input = wrap ? wrap.querySelector("input") : null;
      if (!input) return;
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      passwordToggle.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
      var use = passwordToggle.querySelector("use");
      if (use) {
        var href = (use.getAttribute("href") || "").split("#")[0];
        use.setAttribute("href", href + (show ? "#visibility_off" : "#visibility"));
      }
    });
  });

  document.querySelectorAll("[data-demo-recovery]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var card = form.closest(".auth__card");
      var formState = card && card.querySelector("[data-demo-recovery-form-state]");
      var successState = card && card.querySelector("[data-demo-recovery-success]");
      var emailField = form.querySelector('input[type="email"]');
      var emailTarget = successState && successState.querySelector("[data-demo-recovery-email]");
      if (emailTarget && emailField) emailTarget.textContent = emailField.value;
      if (formState && successState) {
        formState.hidden = true;
        successState.hidden = false;
        return;
      }
      var message = form.querySelector("[data-demo-recovery-message]");
      if (message) message.hidden = false;
    });
  });

  document.querySelectorAll("[data-google-unavailable]").forEach(function (button) {
    button.addEventListener("click", function () {
      var notice = document.querySelector("[data-google-auth-message]");
      if (notice) notice.hidden = false;
    });
  });

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
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(unitPrice * units);
      total.textContent = "$" + formatted;
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
