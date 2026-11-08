(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_6 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x282 (= s_6 (_ bv15 4))))
(not $x282)))
(check-sat)
