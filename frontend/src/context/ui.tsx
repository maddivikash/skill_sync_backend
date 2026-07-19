import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";

/* ============================================================
   App-wide UI feedback: toasts + promise-based confirm dialog.
   Replaces native alert()/confirm() with styled, on-brand UI.
   ============================================================ */

type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
}

interface UIContextValue {
  toast: (message: string, kind?: ToastKind) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const UIContext = createContext<UIContextValue | null>(null);

const ICONS: Record<ToastKind, string> = {
  success: "✓",
  error: "!",
  info: "i",
};

export function UIProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmState, setConfirmState] = useState<{
    options: ConfirmOptions;
    resolve: (v: boolean) => void;
  } | null>(null);
  const nextId = useRef(1);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, kind: ToastKind = "info") => {
      const id = nextId.current++;
      setToasts((prev) => [...prev, { id, kind, message }]);
      window.setTimeout(() => remove(id), 3800);
    },
    [remove]
  );

  const success = useCallback((m: string) => toast(m, "success"), [toast]);
  const error = useCallback((m: string) => toast(m, "error"), [toast]);
  const info = useCallback((m: string) => toast(m, "info"), [toast]);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setConfirmState({ options, resolve });
    });
  }, []);

  function closeConfirm(result: boolean) {
    confirmState?.resolve(result);
    setConfirmState(null);
  }

  return (
    <UIContext.Provider value={{ toast, success, error, info, confirm }}>
      {children}

      {/* Toasts */}
      <div className="toast-stack" role="region" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.kind}`}>
            <span className="toast__icon" aria-hidden="true">
              {ICONS[t.kind]}
            </span>
            <span className="toast__msg">{t.message}</span>
            <button
              className="toast__close"
              onClick={() => remove(t.id)}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Confirm dialog */}
      {confirmState && (
        <div
          className="modal-overlay"
          onClick={() => closeConfirm(false)}
        >
          <div
            className="modal modal--confirm"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="modal__header">
              <h3 className="modal__title">
                {confirmState.options.title ?? "Are you sure?"}
              </h3>
            </div>
            <div className="modal__body">
              <p className="confirm__message">{confirmState.options.message}</p>
              <div className="form__actions">
                <button
                  className="btn btn--ghost"
                  onClick={() => closeConfirm(false)}
                  autoFocus
                >
                  {confirmState.options.cancelText ?? "Cancel"}
                </button>
                <button
                  className={`btn ${
                    confirmState.options.danger ? "btn--danger" : "btn--primary"
                  }`}
                  onClick={() => closeConfirm(true)}
                >
                  {confirmState.options.confirmText ?? "Confirm"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </UIContext.Provider>
  );
}

export function useUI(): UIContextValue {
  const ctx = useContext(UIContext);
  if (!ctx) throw new Error("useUI must be used within UIProvider");
  return ctx;
}

export function useToast() {
  const { toast, success, error, info } = useUI();
  return { toast, success, error, info };
}

export function useConfirm() {
  return useUI().confirm;
}
