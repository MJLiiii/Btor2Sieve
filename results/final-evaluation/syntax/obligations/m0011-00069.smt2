(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x5024 (bvuge i_2 (_ bv8 4))))
(not $x5024)))
(check-sat)
