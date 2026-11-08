(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x71 (= i_8 (_ bv0 4))))
(not $x71)))
(check-sat)
