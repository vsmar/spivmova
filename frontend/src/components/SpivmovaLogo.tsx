import { motion, AnimatePresence } from "motion/react";
import { useEffect, useState } from "react";

const CYR = ["С", "п", "і", "в", "м", "о", "в", "а"];
const LAT = ["S", "p", "i", "v", "m", "o", "v", "a"];

export function SpivmovaLogo() {
  const [latin, setLatin] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setLatin((l) => !l), 5000);
    return () => clearInterval(id);
  }, []);

  const letters = latin ? LAT : CYR;

  return (
    <h1 
    aria-label="Spivmova" class="logo" style={{ display: "flex" }}>
      {letters.map((ch, i) => (
        <span
            key={i}
            style={{
                display: "inline-block",
                overflow: "hidden",
                padding: "0.2em 0.04em",
                margin: "-0.2em -0.04em",
                lineHeight: 1.2,
            }}
        >
         {/* <span key={i} style={{ display: "inline-block", overflow: "hidden" }}> */}
          <AnimatePresence mode="popLayout" initial={false}>
            <motion.span
                key={ch}
                className={CYR.includes(ch) ? "logo-blue" : "logo-yellow"}
                initial={{ y: "100%", opacity: 0, rotate: -12 }}
                animate={{ y: 0, opacity: 1, rotate: 0 }}
                exit={{ y: "-100%", opacity: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 18, delay: i * 0.06 }}
                style={{
                    display: "inline-block",
                    fontFamily: latin ? "'Your Latin Font'" : "'Your Cyrillic Font'",
                }}
            >
                {ch}
            </motion.span>
          </AnimatePresence>
        </span>
      ))}
    </h1>
  );
}