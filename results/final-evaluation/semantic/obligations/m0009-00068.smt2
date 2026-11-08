(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x13 (bvsle s_7 (_ bv0 8))))
(not $x13)))
(check-sat)
