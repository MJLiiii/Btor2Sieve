(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1033 (and (distinct i_6 (_ bv0 8)) true)))
(not $x1033)))
(check-sat)
