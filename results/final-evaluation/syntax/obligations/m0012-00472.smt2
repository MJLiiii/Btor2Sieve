(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x14 (bvuge i_4 (_ bv4 3))))
(not $x14)))
(check-sat)
