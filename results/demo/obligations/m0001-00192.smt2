(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_8 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x149 (bvuge i_8 (_ bv7 4))))
(not $x149)))
(check-sat)
