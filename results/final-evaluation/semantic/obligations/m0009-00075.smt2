(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x133 (bvsge s_7 (_ bv1 8))))
(not $x133)))
(check-sat)
