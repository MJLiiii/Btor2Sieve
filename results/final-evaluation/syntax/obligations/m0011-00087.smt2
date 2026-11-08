(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_4 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2305 (bvsge s_4 (_ bv15 4))))
(not $x2305)))
(check-sat)
