(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x7186 (and (distinct i_6 (_ bv128 8)) true)))
(not $x7186)))
(check-sat)
