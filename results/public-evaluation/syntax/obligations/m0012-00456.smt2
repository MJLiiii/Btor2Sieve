(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x1556 (and (distinct i_4 (_ bv0 3)) true)))
(not $x1556)))
(check-sat)
