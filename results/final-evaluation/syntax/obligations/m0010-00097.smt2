(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x4131 (bvule i_6 (_ bv1 8))))
(not $x4131)))
(check-sat)
