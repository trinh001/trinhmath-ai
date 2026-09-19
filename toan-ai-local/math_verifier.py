"""Math Verifier V1 cho các khẳng định được cấu trúc rõ ràng.

Module không đọc đề tự do để "đoán" công thức. Người gọi phải cung cấp biểu
thức SymPy có cấu trúc; mọi dữ liệu thiếu, LaTeX chưa chuyển đổi hoặc dạng chưa
hỗ trợ trả về INCONCLUSIVE/UNSUPPORTED thay vì VERIFIED.
"""

from __future__ import annotations

import re
from typing import Any


VERIFIED = "VERIFIED"
CONTRADICTED = "CONTRADICTED"
INCONCLUSIVE = "INCONCLUSIVE"
UNSUPPORTED = "UNSUPPORTED"


_SAFE_EXPRESSION_CHARS = re.compile(r"[0-9A-Za-z_+\-*/^().,\s]+\Z")
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_FUNCTION_CALL = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*\(")
_SAFE_FUNCTIONS = frozenset({
    "Abs", "acos", "acosh", "asin", "asinh", "atan", "atanh", "binomial",
    "cos", "cosh", "exp", "factorial", "log", "sin", "sinh", "sqrt", "tan", "tanh",
})
_PYTHON_KEYWORDS = frozenset({
    "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del",
    "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in",
    "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while",
    "with", "yield",
})


def _result(status: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"status": status, "message": message, "evidence": evidence}


def _sympy():
    """Nạp SymPy trễ để app không phải trả chi phí khởi động khi không xác minh."""
    import sympy  # Imported only when a teacher/service explicitly requests verification.
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        parse_expr,
        standard_transformations,
    )
    return sympy, parse_expr, standard_transformations + (convert_xor, implicit_multiplication_application)


def _safe_expression_text(expression: object) -> str:
    """Chỉ nhận cú pháp đại số, trước khi SymPy parse expression bằng eval nội bộ.

    Giáo viên vẫn có thể dùng biến tự do và một nhóm hàm Toán phổ biến. Các
    chuỗi kiểu mã Python, thuộc tính, chuỗi ký tự hay hàm không có trong danh
    sách rõ ràng bị trả về INCONCLUSIVE thay vì được gửi vào parser.
    """
    if expression is None or not str(expression).strip():
        raise ValueError("Thiếu biểu thức cần xác minh.")
    raw = str(expression).strip()
    if "\\" in raw or "$" in raw:
        raise ValueError("Math Verifier V1 chưa nhận LaTeX trực tiếp; cần biểu thức SymPy có cấu trúc.")
    normalized = raw.replace("−", "-").replace("×", "*").replace("÷", "/")
    if not _SAFE_EXPRESSION_CHARS.fullmatch(normalized):
        raise ValueError("Biểu thức chứa ký tự không thuộc cú pháp Toán được hỗ trợ.")
    if "__" in normalized:
        raise ValueError("Biểu thức chứa tên nội bộ không được phép.")
    for index, character in enumerate(normalized):
        if character == "." and not (
            index > 0 and index + 1 < len(normalized)
            and normalized[index - 1].isdigit() and normalized[index + 1].isdigit()
        ):
            raise ValueError("Dấu chấm chỉ được dùng trong số thập phân.")
    identifiers = {item.group(0).lower() for item in _IDENTIFIER.finditer(normalized)}
    if identifiers & _PYTHON_KEYWORDS:
        raise ValueError("Biểu thức chứa từ khóa lập trình không được phép.")
    for match in _FUNCTION_CALL.finditer(normalized):
        if match.group(1) not in _SAFE_FUNCTIONS:
            raise ValueError(f"Hàm `{match.group(1)}` chưa được Math Verifier hỗ trợ.")
    return normalized


def _parse(expression: object):
    raw = _safe_expression_text(expression)
    sympy, parse_expr, transformations = _sympy()
    return sympy, parse_expr(raw, transformations=transformations)


def _symbol(sympy, variable: object):
    name = str(variable or "x").strip()
    if not name.isidentifier():
        raise ValueError("Biến số phải là một tên đơn giản, ví dụ x.")
    return sympy.Symbol(name)


def verify_equation_solution(claim: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra một nghiệm bằng thế trực tiếp và loại trường hợp ngoài miền xác định."""
    try:
        sympy, lhs = _parse(claim.get("lhs"))
        _, rhs = _parse(claim.get("rhs"))
        _, candidate = _parse(claim.get("candidate"))
        variable = _symbol(sympy, claim.get("variable", "x"))
        difference = sympy.together(lhs - rhs)
        numerator, denominator = sympy.fraction(difference)
        denominator_value = sympy.simplify(denominator.subs(variable, candidate))
        if denominator_value == 0 or denominator_value in {sympy.zoo, sympy.nan}:
            return _result(
                CONTRADICTED,
                "Giá trị được nêu làm nghiệm nằm ngoài miền xác định của phương trình.",
                variable=str(variable),
                candidate=str(candidate),
            )
        residual = sympy.simplify(numerator.subs(variable, candidate))
        if residual == 0:
            return _result(
                VERIFIED,
                "Thế nghiệm vào phương trình cho vế trái trừ vế phải bằng 0.",
                variable=str(variable),
                candidate=str(candidate),
                residual=str(residual),
            )
        return _result(
            CONTRADICTED,
            "Thế nghiệm vào phương trình không cho giá trị bằng 0.",
            variable=str(variable),
            candidate=str(candidate),
            residual=str(residual),
        )
    except (ImportError, TypeError, ValueError, SyntaxError) as error:
        return _result(INCONCLUSIVE, f"Không thể xác minh phương trình từ dữ liệu được cung cấp: {error}")
    except Exception as error:  # SymPy may raise diverse domain-specific exceptions.
        return _result(INCONCLUSIVE, f"Xác minh phương trình chưa kết luận được: {error}")


def verify_derivative(claim: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra f'(x) bằng đồng nhất thức ký hiệu."""
    try:
        sympy, function = _parse(claim.get("function"))
        _, claimed_derivative = _parse(claim.get("derivative"))
        variable = _symbol(sympy, claim.get("variable", "x"))
        residual = sympy.simplify(sympy.diff(function, variable) - claimed_derivative)
        if residual == 0:
            return _result(VERIFIED, "Đạo hàm SymPy đồng nhất với kết quả được nêu.", variable=str(variable))
        return _result(CONTRADICTED, "Đạo hàm SymPy không đồng nhất với kết quả được nêu.", variable=str(variable), residual=str(residual))
    except (ImportError, TypeError, ValueError, SyntaxError) as error:
        return _result(INCONCLUSIVE, f"Không thể xác minh đạo hàm từ dữ liệu được cung cấp: {error}")
    except Exception as error:
        return _result(INCONCLUSIVE, f"Xác minh đạo hàm chưa kết luận được: {error}")


def verify_antiderivative(claim: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra F là một nguyên hàm bằng cách đạo hàm F."""
    try:
        sympy, integrand = _parse(claim.get("integrand"))
        _, antiderivative = _parse(claim.get("antiderivative"))
        variable = _symbol(sympy, claim.get("variable", "x"))
        residual = sympy.simplify(sympy.diff(antiderivative, variable) - integrand)
        if residual == 0:
            return _result(VERIFIED, "Đạo hàm nguyên hàm được nêu bằng integrand.", variable=str(variable))
        return _result(CONTRADICTED, "Đạo hàm nguyên hàm được nêu không bằng integrand.", variable=str(variable), residual=str(residual))
    except (ImportError, TypeError, ValueError, SyntaxError) as error:
        return _result(INCONCLUSIVE, f"Không thể xác minh nguyên hàm từ dữ liệu được cung cấp: {error}")
    except Exception as error:
        return _result(INCONCLUSIVE, f"Xác minh nguyên hàm chưa kết luận được: {error}")


def verify_definite_integral(claim: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra tích phân xác định bằng tính toán ký hiệu chính xác khi hỗ trợ."""
    try:
        sympy, integrand = _parse(claim.get("integrand"))
        _, lower = _parse(claim.get("lower"))
        _, upper = _parse(claim.get("upper"))
        _, claimed_value = _parse(claim.get("value"))
        variable = _symbol(sympy, claim.get("variable", "x"))
        computed = sympy.integrate(integrand, (variable, lower, upper))
        residual = sympy.simplify(computed - claimed_value)
        if residual == 0:
            return _result(VERIFIED, "Tích phân ký hiệu bằng giá trị được nêu.", variable=str(variable), value=str(computed))
        return _result(CONTRADICTED, "Tích phân ký hiệu không bằng giá trị được nêu.", variable=str(variable), computed=str(computed), residual=str(residual))
    except (ImportError, TypeError, ValueError, SyntaxError) as error:
        return _result(INCONCLUSIVE, f"Không thể xác minh tích phân từ dữ liệu được cung cấp: {error}")
    except Exception as error:
        return _result(INCONCLUSIVE, f"Xác minh tích phân chưa kết luận được: {error}")


def verify_expression_equivalence(claim: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra hai biểu thức có đồng nhất hay không bằng simplify(lhs-rhs)."""
    try:
        sympy, lhs = _parse(claim.get("lhs"))
        _, rhs = _parse(claim.get("rhs"))
        residual = sympy.simplify(lhs - rhs)
        if residual == 0:
            return _result(VERIFIED, "Hai biểu thức đồng nhất theo SymPy.")
        return _result(CONTRADICTED, "Hai biểu thức không đồng nhất theo SymPy.", residual=str(residual))
    except (ImportError, TypeError, ValueError, SyntaxError) as error:
        return _result(INCONCLUSIVE, f"Không thể xác minh hai biểu thức từ dữ liệu được cung cấp: {error}")
    except Exception as error:
        return _result(INCONCLUSIVE, f"Xác minh biểu thức chưa kết luận được: {error}")


def verify_math_claim(claim: object) -> dict[str, Any]:
    """Điểm vào duy nhất cho payload có `kind` rõ ràng, dùng cho review service sau này."""
    if not isinstance(claim, dict):
        return _result(INCONCLUSIVE, "Dữ liệu xác minh phải là một đối tượng có cấu trúc.")
    handlers = {
        "equation_solution": verify_equation_solution,
        "derivative": verify_derivative,
        "antiderivative": verify_antiderivative,
        "definite_integral": verify_definite_integral,
        "expression_equivalence": verify_expression_equivalence,
    }
    handler = handlers.get(str(claim.get("kind") or "").strip())
    if not handler:
        return _result(UNSUPPORTED, "Dạng Toán này chưa có bộ kiểm chứng tự động; cần giáo viên duyệt.")
    return handler(claim)


def math_verification_release_issue(variant: object) -> str:
    """Không cho phát hành nếu một kết quả xác minh đã được lưu nhưng không đạt.

    Variant lịch sử chưa có trường này không bị thay đổi trạng thái. Khi một
    luồng mới chủ động thêm kết quả verifier, `INCONCLUSIVE` và `UNSUPPORTED`
    vẫn buộc giáo viên duyệt thay vì bị hiểu nhầm là xác minh thành công.
    """
    if not isinstance(variant, dict):
        return ""
    result = variant.get("math_verification")
    if not isinstance(result, dict):
        return ""
    status = str(result.get("status") or "").strip().upper()
    if status == VERIFIED:
        return ""
    if status == CONTRADICTED:
        return "Math Verifier phát hiện mâu thuẫn với khẳng định Toán học; không thể phát hành."
    if status in {INCONCLUSIVE, UNSUPPORTED}:
        return "Math Verifier chưa xác minh được nội dung này; cần giáo viên kiểm tra trước khi phát hành."
    return "Trạng thái Math Verifier không hợp lệ; cần giáo viên kiểm tra trước khi phát hành."
