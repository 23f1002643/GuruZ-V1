"""Text utilities for scientific and mathematical formatting.

Normalizes chemical formulas, subscripts, superscripts, and Greek symbols
so they render correctly in PDFs and web output.
"""
from __future__ import annotations
import re

# Unicode subscript / superscript maps
_SUBSCRIPTS = str.maketrans(
    "0123456789+-=()",
    "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎",
)
_SUPERSCRIPTS = str.maketrans(
    "0123456789+-=()",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾",
)

# Common chemical element symbols (for formula detection)
_ELEMENTS = sorted(
    [
        "Ac", "Ag", "Al", "Am", "Ar", "As", "At", "Au", "B", "Ba", "Be",
        "Bh", "Bi", "Bk", "Br", "C", "Ca", "Cd", "Ce", "Cf", "Cl", "Cm",
        "Cn", "Co", "Cr", "Cs", "Cu", "Db", "Ds", "Dy", "Er", "Es", "Eu",
        "F", "Fe", "Fl", "Fm", "Fr", "Ga", "Gd", "Ge", "H", "He", "Hf",
        "Hg", "Ho", "Hs", "I", "In", "Ir", "K", "Kr", "La", "Li", "Lr",
        "Lu", "Lv", "Mc", "Md", "Mg", "Mn", "Mo", "Mt", "N", "Na", "Nb",
        "Nd", "Ne", "Nh", "Ni", "No", "Np", "O", "Og", "Os", "P", "Pa",
        "Pb", "Pd", "Pm", "Po", "Pr", "Pt", "Pu", "Rb", "Re", "Rf", "Rg",
        "Rh", "Rn", "Ru", "S", "Sb", "Sc", "Se", "Sg", "Si", "Sm", "Sn",
        "Sr", "Ta", "Tb", "Tc", "Te", "Th", "Ti", "Tl", "Tm", "Ts", "U",
        "V", "W", "Xe", "Y", "Yb", "Zn", "Zr",
    ],
    key=len,
    reverse=True,
)


def to_subscript(text: str) -> str:
    """Convert ASCII digits to Unicode subscripts."""
    return text.translate(_SUBSCRIPTS)


def to_superscript(text: str) -> str:
    """Convert ASCII digits to Unicode superscripts."""
    return text.translate(_SUPERSCRIPTS)


_CHEMICAL_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(e) for e in _ELEMENTS) + r")"
    r"(?:\d+)*"
    r"(?:\([^\)]*\)\d*)*"
    r"\d*"
)


def _normalize_chemicals(text: str) -> str:
    """Convert chemical formulas like C6H12O6 to C₆H₁₂O₆."""
    def repl(match: re.Match) -> str:
        formula = match.group(0)
        # Convert digits that follow an element symbol to subscripts.
        out: list[str] = []
        i = 0
        while i < len(formula):
            ch = formula[i]
            # Handle parentheses groups: (OH)2
            if ch == "(":
                j = formula.find(")", i)
                if j != -1:
                    group = formula[i : j + 1]
                    k = j + 1
                    count = ""
                    while k < len(formula) and formula[k].isdigit():
                        count += formula[k]
                        k += 1
                    out.append(group)
                    if count:
                        out.append(to_subscript(count))
                    i = k
                    continue
            if ch.isdigit():
                out.append(to_subscript(ch))
            else:
                out.append(ch)
            i += 1
        return "".join(out)

    return _CHEMICAL_RE.sub(repl, text)


_GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "omicron": "ο",
    "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ",
    "phi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Alpha": "Α", "Beta": "Β", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ",
    "Lambda": "Λ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Omega": "Ω",
    "infty": "∞", "infinity": "∞", "deg": "°",
}


def normalize_scientific(text: str) -> str:
    """Apply all scientific/math formatting normalizations."""
    if not text:
        return text or ""

    result = text

    # Superscripts: x^2, a^2, H2O^2 etc.
    result = re.sub(r"([A-Za-z0-9)\]])\(?\^([0-9+-]+)\)?", lambda m: m.group(1) + to_superscript(m.group(2)), result)
    # Subscripts via underscore
    result = re.sub(r"([A-Za-z0-9)\]])_\{([^}]+)\}", lambda m: m.group(1) + to_subscript(m.group(2)), result)
    result = re.sub(r"([A-Za-z0-9)\]])_([0-9]+)", lambda m: m.group(1) + to_subscript(m.group(2)), result)

    # Chemical formulas
    result = _normalize_chemicals(result)

    # Greek word names -> symbols
    for word, symbol in _GREEK.items():
        # Replace word standing alone (word boundary)
        result = re.sub(rf"\b{re.escape(word)}\b", symbol, result)

    return result
