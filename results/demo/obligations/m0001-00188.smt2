(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x154 (bvuge i_8 (_ bv8 4))))
(not $x154)))
(check-sat)
