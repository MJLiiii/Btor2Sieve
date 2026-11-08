(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1179 (and (distinct i_7 (_ bv1 8)) true)))
(not $x1179)))
(check-sat)
