from math_verifier import (
    CONTRADICTED,
    INCONCLUSIVE,
    UNSUPPORTED,
    VERIFIED,
    math_verification_release_issue,
    verify_math_claim,
)


def test_equation_solution_checks_substitution_and_domain():
    verified = verify_math_claim({
        "kind": "equation_solution", "lhs": "x**2 - 1", "rhs": "0", "variable": "x", "candidate": "1",
    })
    wrong = verify_math_claim({
        "kind": "equation_solution", "lhs": "x**2 - 1", "rhs": "0", "variable": "x", "candidate": "2",
    })
    outside_domain = verify_math_claim({
        "kind": "equation_solution", "lhs": "1/(x - 1)", "rhs": "0", "variable": "x", "candidate": "1",
    })
    assert verified["status"] == VERIFIED
    assert wrong["status"] == CONTRADICTED
    assert outside_domain["status"] == CONTRADICTED


def test_derivative_antiderivative_integral_and_equivalence():
    assert verify_math_claim({
        "kind": "derivative", "function": "x**3", "derivative": "3*x**2", "variable": "x",
    })["status"] == VERIFIED
    assert verify_math_claim({
        "kind": "antiderivative", "integrand": "2*x", "antiderivative": "x**2", "variable": "x",
    })["status"] == VERIFIED
    assert verify_math_claim({
        "kind": "definite_integral", "integrand": "x", "lower": "0", "upper": "2", "value": "2", "variable": "x",
    })["status"] == VERIFIED
    assert verify_math_claim({
        "kind": "expression_equivalence", "lhs": "(x + 1)**2", "rhs": "x**2 + 2*x + 1",
    })["status"] == VERIFIED


def test_unknown_or_latex_input_never_becomes_verified():
    assert verify_math_claim({"kind": "geometry_proof"})["status"] == UNSUPPORTED
    assert verify_math_claim({"kind": "derivative", "function": "$x^2$", "derivative": "2*x"})["status"] == INCONCLUSIVE


def test_verifier_rejects_non_math_function_calls_before_sympy_parses_them():
    unsafe = verify_math_claim({"kind": "derivative", "function": "open(1)", "derivative": "0"})
    safe = verify_math_claim({"kind": "derivative", "function": "sin(x)", "derivative": "cos(x)"})

    assert unsafe["status"] == INCONCLUSIVE
    assert "chưa được Math Verifier hỗ trợ" in unsafe["message"]
    assert safe["status"] == VERIFIED


def test_release_gate_interprets_math_status_conservatively():
    assert math_verification_release_issue({}) == ""
    assert math_verification_release_issue({"math_verification": {"status": VERIFIED}}) == ""
    assert "mâu thuẫn" in math_verification_release_issue({"math_verification": {"status": CONTRADICTED}})
    assert "giáo viên" in math_verification_release_issue({"math_verification": {"status": INCONCLUSIVE}})
