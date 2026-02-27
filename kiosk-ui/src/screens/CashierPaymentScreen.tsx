import { useMemo } from "react";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Banknote } from "lucide-react";
import { Button } from "../components/ui/Button";
import { HeaderBar } from "../components/layout/HeaderBar";
import { BottomNav } from "../components/layout/BottomNav";
import { useSessionStore } from "../store/sessionStore";

interface CashierPaymentScreenProps {
  onDone: () => void;
  onBack: () => void;
}

export function CashierPaymentScreen({
  onDone,
  onBack,
}: CashierPaymentScreenProps) {
  const { t } = useTranslation();
  const currentService = useSessionStore((s) => s.currentService);

  const amountFormatted = useMemo(() => {
    if (!currentService?.price_uzs) return "";
    return `${new Intl.NumberFormat("uz-UZ").format(currentService.price_uzs)} ${t("common.somCurrency")}`;
  }, [currentService, t]);

  return (
    <motion.div
      className="relative flex h-screen w-screen flex-col overflow-hidden"
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -60 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <HeaderBar title={t("payment.title")} />

      <div className="flex flex-1 flex-col items-center justify-center px-8">
        {/* Icon */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{
            type: "spring" as const,
            stiffness: 200,
            damping: 15,
            delay: 0.2,
          }}
          className="flex h-28 w-28 items-center justify-center rounded-full bg-primary-50"
        >
          <Banknote className="h-14 w-14 text-primary" />
        </motion.div>

        {/* Title */}
        <motion.h2
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-8 text-h1 tracking-heading text-text-primary"
        >
          {t("payment.cashierTitle")}
        </motion.h2>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-4 max-w-md text-center text-body-lg text-text-muted"
        >
          {t("payment.cashierDesc")}
        </motion.p>

        {/* Amount if available */}
        {amountFormatted && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="mt-6 rounded-card bg-white px-8 py-4 shadow-card"
          >
            <p className="text-center text-caption text-text-muted">
              {t("payment.amount")}
            </p>
            <p className="mt-1 text-center text-h2 font-bold text-text-primary">
              {amountFormatted}
            </p>
          </motion.div>
        )}

        {/* Done button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="mt-8 w-full max-w-xs"
        >
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={onDone}
          >
            {t("common.ok")}
          </Button>
        </motion.div>
      </div>

      <BottomNav onBack={onBack} />
    </motion.div>
  );
}
