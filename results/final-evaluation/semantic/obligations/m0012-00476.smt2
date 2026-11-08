(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x30 (bvuge i_4 (_ bv3 3))))
(not $x30)))
(check-sat)
