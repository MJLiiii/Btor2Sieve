(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x83 (bvsge s_3 (_ bv15 4))))
(not $x83)))
(check-sat)
