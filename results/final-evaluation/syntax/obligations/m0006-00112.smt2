(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x446 (bvsle s_3 (_ bv0 4))))
(not $x446)))
(check-sat)
