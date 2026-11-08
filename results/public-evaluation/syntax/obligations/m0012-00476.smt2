(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x45 (bvuge i_4 (_ bv3 3))))
(not $x45)))
(check-sat)
