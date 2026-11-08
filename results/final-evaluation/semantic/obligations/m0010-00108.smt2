(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x1605 (and (distinct i_6 (_ bv128 8)) true)))
(not $x1605)))
(check-sat)
