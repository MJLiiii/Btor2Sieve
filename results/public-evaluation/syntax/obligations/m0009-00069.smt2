(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x550 (bvsge s_7 (_ bv0 8))))
(not $x550)))
(check-sat)
