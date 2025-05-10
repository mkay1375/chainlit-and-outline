chainlitCopilot = {
  handleCopilotFunctionEvents: function () {
    window.addEventListener("chainlit-call-fn", (e) => {
      const {name, args, callback} = e.detail;
      if (name === "page-url") {
        callback(window.location.href);
      } else {
        callback(`Unsupported function '${name}'`);
      }
    });
  },
  mountCopilot: function () {
    function getAccessToken() {
      if (typeof chainlitCopilotJwt !== 'undefined') {
        return chainlitCopilotJwt;
      }
      return "";
    }

    window.mountChainlitWidget({
      chainlitServer: "http://localhost:8000",
      theme: 'dark',
      // accessToken: getAccessToken(),
    });
  },
  fixCopilotStyleAndKeyboardShortcutsConflict: function () {
    window.addEventListener('load', function () {
      const checkInterval = setInterval(() => {
        console.log("f1");
        const copilotElement = document.getElementById('chainlit-copilot');
        console.log("f2", copilotElement);
        if (copilotElement && copilotElement.shadowRoot) {
          const sheet = new CSSStyleSheet();
          const customCss = `
          #chainlit-copilot-button {
              bottom: 4rem;
          }

          #cl-shadow-root div[role=dialog] {
              max-height: calc(100vh - 212px);
          }

          div[data-radix-popper-content-wrapper] {
              z-index: 9999 !important;
          }
          `;
          sheet.replaceSync(customCss);
          copilotElement.shadowRoot.adoptedStyleSheets.push(sheet);

          copilotElement.shadowRoot.addEventListener('keydown', function (event) {
            if (event.key !== 'Enter') event.stopPropagation();
          }, true);

          clearInterval(checkInterval); // Stop checking once we've found and modified the element
        }
      }, 1000);
    });
  },
  handleCopilotVisibilityInPages: function () {
    (() => {
      let oldPushState = history.pushState;
      history.pushState = function pushState() {
        let ret = oldPushState.apply(this, arguments);
        window.dispatchEvent(new Event('pushstate'));
        window.dispatchEvent(new Event('locationchange'));
        return ret;
      };

      let oldReplaceState = history.replaceState;
      history.replaceState = function replaceState() {
        let ret = oldReplaceState.apply(this, arguments);
        window.dispatchEvent(new Event('replacestate'));
        window.dispatchEvent(new Event('locationchange'));
        return ret;
      };

      window.addEventListener('popstate', () => {
        window.dispatchEvent(new Event('locationchange'));
      });
    })();

    window.addEventListener('locationchange', function (e) {
      const path = window.location.pathname;
      const showOnPaths = ['/home', '/doc', '/collection', '/search', '/drafts', '/archive', '/trash'];
      const shouldShow = showOnPaths.some(p => path.startsWith(p));

      const copilotElement = document.getElementById('chainlit-copilot');
      if (copilotElement) {
        copilotElement.style.display = shouldShow ? 'block' : 'none';
      }
    });
  }
}

chainlitCopilot.handleCopilotFunctionEvents();
chainlitCopilot.handleCopilotVisibilityInPages();
chainlitCopilot.mountCopilot();
chainlitCopilot.fixCopilotStyleAndKeyboardShortcutsConflict();
